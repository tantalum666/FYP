import Foundation
import Vision
let expected = "SP-E5B968D0FE"
let valid = ["SP-E5B968D0FE", " sp-e5b968d0fe \n", "senplate://menu/SP-E5B968D0FE", "SENPLATE://MENU/sp-e5b968d0fe"]
for input in valid { precondition(MenuCode.parse(input) == expected) }
let invalid = ["https://example.com/menu/SP-E5B968D0FE", "senplate://admin/SP-E5B968D0FE", "senplate://user@menu/SP-E5B968D0FE", "senplate://menu:443/SP-E5B968D0FE", "senplate://menu/SP-E5B968D0FE?role=manager", "senplate://menu/SP-E5B968D0FE#x", "senplate://menu/SP-E5B968D0FE/extra", "short", "ＳＰ-E5B968D0FE"]
for input in invalid { precondition(MenuCode.parse(input) == nil, input) }
let request = VNDetectBarcodesRequest(); request.symbologies = [.qr]
try VNImageRequestHandler(url: URL(fileURLWithPath: CommandLine.arguments[1])).perform([request])
let codes = (request.results ?? []).compactMap(\.payloadStringValue)
precondition(codes == ["senplate://menu/" + expected], "QR contents: \(codes)")
print("PASS: 4 accepted and 9 rejected menu inputs; actual browser-rendered QR decoded as \(codes[0]).")
