from cicada.languages.gleam.formatter import GleamFormatter


def test_format_function_identifier():
    formatter = GleamFormatter()

    assert (
        formatter.format_function_identifier("wardwright/lustre_model_access", "update", 2)
        == "wardwright/lustre_model_access.update/2"
    )


def test_format_function_name_with_args():
    formatter = GleamFormatter()

    assert formatter.format_function_name("update", 2, ["model", "msg"]) == "update(model, msg)"
    assert formatter.format_function_name("init", 0) == "init/0"
