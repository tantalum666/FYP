import Foundation

enum MenuCode {
    static func parse(_ input: String) -> String? {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        let code: String
        if text.lowercased().hasPrefix("senplate://") {
            guard let url = URLComponents(string: text), url.scheme?.lowercased() == "senplate",
                  url.host?.lowercased() == "menu", url.user == nil, url.password == nil,
                  url.port == nil, url.query == nil, url.fragment == nil else { return nil }
            let parts = url.path.split(separator: "/", omittingEmptySubsequences: true)
            guard parts.count == 1 else { return nil }
            code = String(parts[0]).uppercased()
        } else { code = text.uppercased() }
        guard !code.hasPrefix("SPM-"), code.range(of: "^[A-Z0-9-]{6,32}$", options: .regularExpression) != nil else { return nil }
        return code
    }
}
