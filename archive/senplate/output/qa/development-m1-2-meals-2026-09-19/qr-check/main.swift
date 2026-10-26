import Foundation
import Vision
let expected = "SPM-6D856EA02DB8"
let valid = [expected, " spm-6d856ea02db8 \n", "senplate://pair/" + expected, "SENPLATE://PAIR/spm-6d856ea02db8"]
for value in valid { precondition(PairCode.parse(value) == expected) }
let invalid = ["SP-E5B968D0FE", "https://example.com/pair/" + expected, "senplate://menu/" + expected, "senplate://person@pair/" + expected, "senplate://pair:443/" + expected, "senplate://pair/" + expected + "?role=manager", "senplate://pair/" + expected + "#x", "senplate://pair/" + expected + "/extra", "SPM-6D856EA02DB", "SPM-6D856EA02DB88", "SPM-6D856EA02DBZ", "ＳＰＭ-6D856EA02DB8"]
for value in invalid { precondition(PairCode.parse(value) == nil, value) }
precondition(MenuCode.parse(expected) == nil)
precondition(MenuCode.parse("senplate://pair/" + expected) == nil)
let request = VNDetectBarcodesRequest(); request.symbologies = [.qr]
try VNImageRequestHandler(url: URL(fileURLWithPath: CommandLine.arguments[1])).perform([request])
let codes = (request.results ?? []).compactMap(\.payloadStringValue)
precondition(codes == ["senplate://pair/" + expected], "Unexpected QR payload: \(codes)")
print("PASS: 4 accepted / 12 rejected pairing inputs; menu parser rejects pairing codes; actual browser QR decoded.")
