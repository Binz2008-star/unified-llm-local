# Gate is in brain_agent_v4.py Agent.chat — unit test the helper _tool_result_failed
def test_tool_result_failed():
    import importlib.util, pathlib

    p = pathlib.Path(__file__).resolve().parent.parent / "brain_agent_v4.py"
    spec = importlib.util.spec_from_file_location("ba", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod._tool_result_failed("Error: fail") is True
    assert mod._tool_result_failed("Exit 1: fail") is True
    assert mod._tool_result_failed("Exit 0: ok") is False
    assert mod._tool_result_failed("Wrote 10 chars") is False
