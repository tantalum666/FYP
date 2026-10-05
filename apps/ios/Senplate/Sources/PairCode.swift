import Foundation

enum PairCode {
    static func parse(_ input: String) -> String? {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        let code: String
        if text.lowercased().hasPrefix("senplate://") {
            guard let url = URLComponents(string: text), url.scheme?.lowercased() == "senplate",
                  url.host?.lowercased() == "pair", url.user == nil, url.password == nil,
                  url.port == nil, url.query == nil, url.fragment == nil else { return nil }
            let parts = url.path.split(separator: "/", omittingEmptySubsequences: true)
            guard parts.count == 1 else { return nil }; code = String(parts[0]).uppercased()
        } else { code = text.uppercased() }
        guard code.range(of: "^SPM-[A-F0-9]{12}$", options: .regularExpression) != nil else { return nil }
        return code
    }
}
