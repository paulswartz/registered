from registered import merge


def test_dedup_prefix():
    assert merge.dedup_prefix(
        ["Prefix-11112020", "Prefix-12122020", "Other-11122020"]
    ) == ["Prefix-12122020", "Other-11122020"]

    assert merge.dedup_prefix(["NoDate"]) == ["NoDate"]

    assert merge.dedup_prefix(iter(["first", "second"])) == ["first", "second"]
