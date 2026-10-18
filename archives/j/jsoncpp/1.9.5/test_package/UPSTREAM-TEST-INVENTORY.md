# JsonCpp 1.9.5 upstream logical test inventory (upstream source 1.9.5)

The identifiers below are counted once across shared/static reruns. CTest wrappers, writer modes, and assertions are not separate logical cases.

## Unit fixtures registered by `src/test_lib_json/main.cpp` (121)

- `ValueTest/checkNormalizeFloatingPointStr`
- `ValueTest/memberCount`
- `ValueTest/objects`
- `ValueTest/arrays`
- `ValueTest/resizeArray`
- `ValueTest/resizePopulatesAllMissingElements`
- `ValueTest/getArrayValue`
- `ValueTest/arrayIssue252`
- `ValueTest/arrayInsertAtRandomIndex`
- `ValueTest/null`
- `ValueTest/strings`
- `ValueTest/bools`
- `ValueTest/integers`
- `ValueTest/nonIntegers`
- `ValueTest/compareNull`
- `ValueTest/compareInt`
- `ValueTest/compareUInt`
- `ValueTest/compareDouble`
- `ValueTest/compareString`
- `ValueTest/compareBoolean`
- `ValueTest/compareArray`
- `ValueTest/compareObject`
- `ValueTest/compareType`
- `ValueTest/CopyObject`
- `ValueTest/typeChecksThrowExceptions`
- `ValueTest/offsetAccessors`
- `ValueTest/StaticString`
- `ValueTest/WideString`
- `ValueTest/CommentBefore`
- `ValueTest/zeroes`
- `ValueTest/zeroesInKeys`
- `ValueTest/specialFloats`
- `ValueTest/precision`
- `ValueTest/searchValueByPath`
- `FastWriterTest/dropNullPlaceholders`
- `FastWriterTest/enableYAMLCompatibility`
- `FastWriterTest/omitEndingLineFeed`
- `FastWriterTest/writeNumericValue`
- `FastWriterTest/writeArrays`
- `FastWriterTest/writeNestedObjects`
- `StyledWriterTest/writeNumericValue`
- `StyledWriterTest/writeArrays`
- `StyledWriterTest/writeNestedObjects`
- `StyledWriterTest/multiLineArray`
- `StyledWriterTest/writeValueWithComment`
- `StyledStreamWriterTest/writeNumericValue`
- `StyledStreamWriterTest/writeArrays`
- `StyledStreamWriterTest/writeNestedObjects`
- `StyledStreamWriterTest/multiLineArray`
- `StyledStreamWriterTest/writeValueWithComment`
- `StreamWriterTest/writeNumericValue`
- `StreamWriterTest/writeArrays`
- `StreamWriterTest/writeNestedObjects`
- `StreamWriterTest/multiLineArray`
- `StreamWriterTest/dropNullPlaceholders`
- `StreamWriterTest/enableYAMLCompatibility`
- `StreamWriterTest/indentation`
- `StreamWriterTest/writeZeroes`
- `StreamWriterTest/unicode`
- `StreamWriterTest/escapeControlCharacters`
- `ReaderTest/parseWithNoErrors`
- `ReaderTest/parseObject`
- `ReaderTest/parseArray`
- `ReaderTest/parseString`
- `ReaderTest/parseComment`
- `ReaderTest/streamParseWithNoErrors`
- `ReaderTest/parseWithNoErrorsTestingOffsets`
- `ReaderTest/parseWithOneError`
- `ReaderTest/parseSpecialFloat`
- `ReaderTest/strictModeParseNumber`
- `ReaderTest/parseChineseWithOneError`
- `ReaderTest/parseWithDetailError`
- `ReaderTest/pushErrorTest`
- `ReaderTest/allowNumericKeysTest`
- `CharReaderTest/parseWithNoErrors`
- `CharReaderTest/parseWithNoErrorsTestingOffsets`
- `CharReaderTest/parseNumber`
- `CharReaderTest/parseString`
- `CharReaderTest/parseComment`
- `CharReaderTest/parseObjectWithErrors`
- `CharReaderTest/parseArrayWithErrors`
- `CharReaderTest/parseWithOneError`
- `CharReaderTest/parseChineseWithOneError`
- `CharReaderTest/parseWithDetailError`
- `CharReaderTest/parseWithStackLimit`
- `CharReaderTest/testOperator`
- `CharReaderStrictModeTest/dupKeys`
- `CharReaderFailIfExtraTest/issue164`
- `CharReaderFailIfExtraTest/issue107`
- `CharReaderFailIfExtraTest/commentAfterObject`
- `CharReaderFailIfExtraTest/commentAfterArray`
- `CharReaderFailIfExtraTest/commentAfterBool`
- `CharReaderFailIfExtraTest/parseComment`
- `CharReaderAllowDropNullTest/issue178`
- `CharReaderAllowNumericKeysTest/allowNumericKeys`
- `CharReaderAllowSingleQuotesTest/issue182`
- `CharReaderAllowZeroesTest/issue176`
- `CharReaderAllowSpecialFloatsTest/specialFloat`
- `CharReaderAllowSpecialFloatsTest/issue209`
- `EscapeSequenceTest/readerParseEscapeSequence`
- `EscapeSequenceTest/charReaderParseEscapeSequence`
- `EscapeSequenceTest/writeEscapeSequence`
- `BuilderTest/settings`
- `BomTest/skipBom`
- `BomTest/notSkipBom`
- `IteratorTest/convert`
- `IteratorTest/decrement`
- `IteratorTest/reverseIterator`
- `IteratorTest/distance`
- `IteratorTest/nullValues`
- `IteratorTest/staticStringKey`
- `IteratorTest/names`
- `IteratorTest/indexes`
- `IteratorTest/constness`
- `RValueTest/moveConstruction`
- `FuzzTest/fuzzDoesntCrash`
- `MemberTemplateAs/BehavesSameAsNamedAs`
- `MemberTemplateIs/BehavesSameAsNamedIs`
- `VersionTest/VersionNumbersMatch`

## Platform exclusion (1, not counted on HarmonyOS)

- `StreamWriterTest/escapeTabCharacterWindows` is guarded by `_WIN32` and is
  therefore not registered by the HarmonyOS `jsoncpp_test` executable.

## Parser/writer data inputs under `test/data` (63 files)

- `test/data/fail_invalid_quote.json`
- `test/data/fail_test_array_01.json`
- `test/data/fail_test_array_02.json`
- `test/data/fail_test_object_01.json`
- `test/data/fail_test_stack_limit.json`
- `test/data/legacy_test_array_01.json`
- `test/data/legacy_test_array_02.json`
- `test/data/legacy_test_array_03.json`
- `test/data/legacy_test_array_04.json`
- `test/data/legacy_test_array_05.json`
- `test/data/legacy_test_array_06.json`
- `test/data/legacy_test_array_07.json`
- `test/data/legacy_test_basic_01.json`
- `test/data/legacy_test_basic_02.json`
- `test/data/legacy_test_basic_03.json`
- `test/data/legacy_test_basic_04.json`
- `test/data/legacy_test_basic_05.json`
- `test/data/legacy_test_basic_06.json`
- `test/data/legacy_test_basic_07.json`
- `test/data/legacy_test_basic_08.json`
- `test/data/legacy_test_basic_09.json`
- `test/data/legacy_test_comment_00.json`
- `test/data/legacy_test_comment_01.json`
- `test/data/legacy_test_comment_02.json`
- `test/data/legacy_test_complex_01.json`
- `test/data/legacy_test_integer_01.json`
- `test/data/legacy_test_integer_02.json`
- `test/data/legacy_test_integer_03.json`
- `test/data/legacy_test_integer_04.json`
- `test/data/legacy_test_integer_05.json`
- `test/data/legacy_test_integer_06_64bits.json`
- `test/data/legacy_test_integer_07_64bits.json`
- `test/data/legacy_test_integer_08_64bits.json`
- `test/data/legacy_test_large_01.json`
- `test/data/legacy_test_object_01.json`
- `test/data/legacy_test_object_02.json`
- `test/data/legacy_test_object_03.json`
- `test/data/legacy_test_object_04.json`
- `test/data/legacy_test_preserve_comment_01.json`
- `test/data/legacy_test_real_01.json`
- `test/data/legacy_test_real_02.json`
- `test/data/legacy_test_real_03.json`
- `test/data/legacy_test_real_04.json`
- `test/data/legacy_test_real_05.json`
- `test/data/legacy_test_real_06.json`
- `test/data/legacy_test_real_07.json`
- `test/data/legacy_test_real_08.json`
- `test/data/legacy_test_real_09.json`
- `test/data/legacy_test_real_10.json`
- `test/data/legacy_test_real_11.json`
- `test/data/legacy_test_real_12.json`
- `test/data/legacy_test_string_01.json`
- `test/data/legacy_test_string_02.json`
- `test/data/legacy_test_string_03.json`
- `test/data/legacy_test_string_04.json`
- `test/data/legacy_test_string_05.json`
- `test/data/legacy_test_string_unicode_01.json`
- `test/data/legacy_test_string_unicode_02.json`
- `test/data/legacy_test_string_unicode_03.json`
- `test/data/legacy_test_string_unicode_04.json`
- `test/data/legacy_test_string_unicode_05.json`
- `test/data/test_array_08.json`
- `test/data/test_object_05.json`

## JSONChecker inputs under `test/jsonchecker` (36 files: 27 runnable, 9 excluded)

Runnable inputs are the `fail{1,2,3,5,6,11,12,14,15,16,17,19,20,21,22,23,24,26,28,29,30,31,32,33}.json`
and `pass{1,2,3}.json` set exercised by the reader/writer test runner.

Excluded by the upstream runner (not counted): `fail4.json`, `fail7.json`,
`fail8.json`, `fail9.json`, `fail10.json`, `fail13.json`, `fail18.json`,
`fail25.json`, `fail27.json`.
