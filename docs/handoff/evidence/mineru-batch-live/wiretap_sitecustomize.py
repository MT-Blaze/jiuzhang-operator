"""真测_wiretap：sitecustomize 导入钩子，包住 mineru_extract 的 _request/_put_raw。

只观测＋委托原函数（HEAD 逻辑一字不动），把四段真_wire 落 JSONL：
POST file-urls/batch（files/data_ids）／PUT（url/body_len/ok）／轮询（batch_id/states）／
zip GET（url/bytes）。另支持控制文件注入「坏图」：JZO_PROBE_INJECT 指向的文件内容
为 corrupt_last 时，把本批最后一份 PUT 的 body 换成坏字节（真上传到 OSS，MinerU
解析失败→逐题账本），用于失败注入跑。绝不改批量逻辑本身。
"""
import sys, os, importlib.abc, threading, json

TARGET = "app.core.ingest.recognize.mineru_extract"
TARGET_MINERU = "app.core.ingest.recognize.mineru"
WIRE = os.environ.get("JZO_PROBE_WIRE", "")
INJECT = os.environ.get("JZO_PROBE_INJECT", "")


def _install():
    if not WIRE:
        return
    lock = threading.Lock()
    state = {"expected_n": 0, "put_counter": 0, "url_index": {}}

    def rec(entry):
        with lock:
            with open(WIRE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def inject_mode():
        if not INJECT:
            return ""
        try:
            return open(INJECT, encoding="utf-8").read().strip()
        except OSError:
            return ""

    def wrap_mineru(mod):
        if getattr(mod, "_probe_wrapped", False):
            return
        mod._probe_wrapped = True
        oprog = mod._progress

        def _progress(callback, route):
            rec({"fn": "_progress", "note": str((route or {}).get("note") or "")})
            return oprog(callback, route)

        mod._progress = _progress

    def wrap(mod):
        if getattr(mod, "_probe_wrapped", False):
            return
        mod._probe_wrapped = True
        oreq, oput = mod._request, mod._put_raw

        def _request(url, *, method="GET", token="", payload=None, timeout=30):
            entry = {"fn": "_request", "url": url, "method": method}
            if payload is not None:
                entry["payload"] = payload
            try:
                out = oreq(url, method=method, token=token, payload=payload, timeout=timeout)
                entry["resp_bytes"] = len(out)
                if "/file-urls/batch" in url and method == "POST":
                    try:
                        doc = json.loads(out.decode("utf-8", "replace"))
                        body = doc.get("data") or {}
                        urls = body.get("file_urls") or []
                        with lock:
                            state["expected_n"] = len(payload.get("files") or []) if payload else 0
                            state["put_counter"] = 0
                            state["url_index"] = {str(u): i for i, u in enumerate(urls)}
                        entry["batch_id"] = body.get("batch_id")
                        entry["file_urls_n"] = len(urls)
                    except Exception:
                        pass
                if "/extract-results/batch/" in url:
                    entry["poll_batch_id"] = url.rsplit("/", 1)[-1]
                    try:
                        doc = json.loads(out.decode("utf-8", "replace"))
                        rows = (doc.get("data") or {}).get("extract_result") or []
                        entry["states"] = [
                            {"data_id": r.get("data_id"), "state": r.get("state"),
                             "err_msg": r.get("err_msg")}
                            for r in rows if isinstance(r, dict)]
                    except Exception:
                        pass
                rec(entry)
                return out
            except Exception as exc:
                entry["error"] = repr(exc)
                rec(entry)
                raise

        def _put_raw(url, data, timeout):
            with lock:
                state["put_counter"] += 1
                idx = state["put_counter"]
                expected = state["expected_n"]
                index = state["url_index"].get(url)
            corrupted = False
            if inject_mode() == "corrupt_last" and expected and idx == expected:
                data = b"\x00\x01\x02CORRUPT-NOT-AN-IMAGE"
                corrupted = True
            entry = {"fn": "_put_raw", "url": url, "body_len": len(data),
                     "put_seq": idx, "file_index": index, "corrupted": corrupted}
            try:
                oput(url, data, timeout)
                entry["ok"] = True
                rec(entry)
            except Exception as exc:
                entry["ok"] = False
                entry["error"] = repr(exc)
                rec(entry)
                raise

        mod._request = _request
        mod._put_raw = _put_raw

    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == TARGET:
                wrapper = wrap
            elif fullname == TARGET_MINERU:
                wrapper = wrap_mineru
            else:
                return None
            spec = None
            for finder in sys.meta_path:
                if finder is self:
                    continue
                try:
                    spec = finder.find_spec(fullname, path, target)
                except Exception:
                    spec = None
                if spec is not None:
                    break
            if spec is None:
                return None
            loader = spec.loader

            class WrapLoader(importlib.abc.Loader):
                def create_module(self, spec):
                    return loader.create_module(spec) if hasattr(loader, "create_module") else None

                def exec_module(self, module):
                    loader.exec_module(module)
                    wrapper(module)

            spec.loader = WrapLoader()
            return spec

    sys.meta_path.insert(0, Finder())


_install()