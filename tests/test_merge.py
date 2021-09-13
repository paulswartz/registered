from registered import merge


def test_dedup_prefix():
    assert merge.dedup_prefix(
        ["Prefix-11112020", "Prefix-12122020", "Other-11122020"]
    ) == ["Prefix-12122020", "Other-11122020"]

    assert merge.dedup_prefix(["NoDate"]) == ["NoDate"]

    assert merge.dedup_prefix(iter(["first", "second"])) == ["first", "second"]

    assert merge.dedup_prefix(
        ["Prefix-11112020.blk", "Prefix-11112020.crw", "Prefix-12122020.crw"]
    ) == ["Prefix-11112020.blk", "Prefix-12122020.crw"]


rename_timepoint_input = """PPAT;   04;Outbound  ; 5;04_ov_2   ;bmipk ;trade ;seasl ;sosta ;prlcg ;const ;atlst ;hayms ;north ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;
PPAT;   19;Inbound   ; 4;19_iv     ;adgal ;fldcr ;genbo ;genco ;ghall ;latac ;warwl ;dudly ;melwa ;malcx ;roxbs ;rugg  ;hrugg ;louis ;brlng ;brkpk ;kenbs ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;
PPAT;   19;Outbound  ; 5;19_ov     ;kenbs ;brkpk ;brlng ;louis ;hrugg ;rugg  ;malcx ;dudly ;warwl ;latac ;ghall ;genco ;genbo ;fldcr ;adgal ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;
"""

rename_timepoint_output = """PPAT;   04;Outbound  ; 5;04_ov_2   ;bmipk ;trade ;seasl ;sosta ;prlcg ;const ;atlst ;hayms ;north ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;
PPAT;   19;Inbound   ; 4;19_iv     ;adgal ;fldcr ;genbo ;genco ;ghall ;latac ;warwl ;nubn  ;melwa ;malcx ;roxbs ;rugg  ;hrugg ;louis ;brlng ;brkpk ;kenbs ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;
PPAT;   19;Outbound  ; 5;19_ov     ;kenbs ;brkpk ;brlng ;louis ;hrugg ;rugg  ;malcx ;nubn  ;warwl ;latac ;ghall ;genco ;genbo ;fldcr ;adgal ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;      ;
"""


def test_rename_timepoint():
    assert merge.rename_timepoint(rename_timepoint_input) == rename_timepoint_output
