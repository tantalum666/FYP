import XCTest

final class MealsUITests: XCTestCase {
    @MainActor private func launch(large: Bool = false) -> XCUIApplication {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchEnvironment["SENPLATE_QA_ENV"] = "meals"
        if large { app.launchArguments = ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"] }
        app.launch()
        return app
    }
    @MainActor private func loginIfNeeded(_ app: XCUIApplication) throws {
        if app.textFields["login.username"].waitForExistence(timeout: 3) {
            let env = ProcessInfo.processInfo.environment
            app.textFields["login.username"].tap()
            app.textFields["login.username"].typeText(try XCTUnwrap(env["SENPLATE_TEST_USERNAME"]) + "\n")
            app.secureTextFields["login.password"].typeText(try XCTUnwrap(env["SENPLATE_TEST_PASSWORD"]) + "\n")
        }
        let profile = app.tabBars.buttons.matching(NSPredicate(format: "label == 'Profile' OR label == '我的'")).firstMatch
        XCTAssertTrue(profile.waitForExistence(timeout: 15)); profile.tap()
        app.buttons["settings.language"].tap(); app.buttons["English"].tap()
        app.tabBars.buttons["Home"].tap()
    }
    @MainActor private func reveal(_ element: XCUIElement, in app: XCUIApplication) {
        XCTAssertTrue(element.waitForExistence(timeout: 12))
        for _ in 0..<8 { if element.isHittable { return }; app.swipeUp() }
        XCTAssertTrue(element.isHittable)
    }
    @MainActor private func openActive(_ app: XCUIApplication) {
        XCTAssertTrue(app.buttons["meal.continue"].waitForExistence(timeout: 15))
        app.buttons["meal.continue"].tap()
        XCTAssertTrue(app.staticTexts["meal.weight"].waitForExistence(timeout: 12))
    }
    @MainActor private func choose(_ slug: String, app: XCUIApplication) {
        let add = app.buttons["meal.add_food"]; reveal(add, in: app); add.tap()
        let reference = app.buttons["reference." + slug]; reveal(reference, in: app); reference.tap()
        let confirm = app.buttons["reference.confirm"]; reveal(confirm, in: app)
        XCTAssertTrue(confirm.isEnabled); confirm.tap()
        XCTAssertTrue(app.buttons["meal.confirm_portion"].waitForExistence(timeout: 12))
    }
    @MainActor private func confirmPortion(_ app: XCUIApplication) {
        let button = app.buttons["meal.confirm_portion"]; reveal(button, in: app)
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate(format: "enabled == true"), object: button)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 12), .completed)
        button.tap()
        XCTAssertTrue(app.buttons["meal.add_food"].waitForExistence(timeout: 10))
    }
    @MainActor func test01RequestPairing() throws {
        let app = launch(); try loginIfNeeded(app)
        app.buttons["meal.connect"].tap()
        let code = app.textFields["pair.code"]; XCTAssertTrue(code.waitForExistence(timeout: 8)); code.tap()
        code.typeText(try XCTUnwrap(ProcessInfo.processInfo.environment["SENPLATE_PAIR_CODE"]) + "\n")
        XCTAssertTrue(app.staticTexts["pair.check"].waitForExistence(timeout: 12))
        XCTAssertEqual(app.staticTexts["pair.check"].label.count, 4)
        attach("01-phone-pair-request")
    }
    @MainActor func test02BeginRice() throws {
        let app = launch(); openActive(app); choose("rice", app: app)
        XCTAssertFalse(app.buttons["meal.confirm_portion"].isEnabled)
        attach("02-phone-rice-start")
    }
    @MainActor func test03RecordAndComplete() async throws {
        let app = launch(); openActive(app)
        XCTAssertEqual(app.staticTexts["meal.weight"].label, "200 g")
        confirmPortion(app)
        choose("chicken", app: app)
        try await simulatedWeight(300)
        confirmPortion(app)
        choose("broccoli", app: app)
        try await simulatedWeight(450)
        confirmPortion(app)
        attach("03-phone-portions")
        let finish = app.buttons["meal.finish_plating"]; reveal(finish, in: app); finish.tap()
        XCTAssertTrue(app.buttons["meal.complete"].waitForExistence(timeout: 12))
        try await simulatedWeight(350)
        let weight = app.staticTexts["meal.weight"]
        let updated = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == '350 g'"), object: weight)
        XCTAssertEqual(XCTWaiter.wait(for: [updated], timeout: 12), .completed)
        let complete = app.buttons["meal.complete"]; reveal(complete, in: app); complete.tap()
        XCTAssertTrue(app.staticTexts["Completed"].waitForExistence(timeout: 12))
        attach("04-phone-completed")
        app.swipeUp(); app.swipeUp()
        XCTAssertTrue(app.staticTexts["nutrition.energy_kcal"].waitForExistence(timeout: 8))
        XCTAssertTrue(app.staticTexts["nutrition.energy_kcal"].label.contains("477.5 kcal"))
        attach("05-phone-reference-nutrition")
    }
    @MainActor func test04RecordsChineseAndLargeType() throws {
        var app = launch(); try loginIfNeeded(app)
        app.tabBars.buttons["Records"].tap()
        app.segmentedControls["records.kind"].buttons["Meals"].tap()
        let row = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH 'meal.record.'")).firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 12)); row.tap()
        XCTAssertTrue(app.staticTexts["Completed"].waitForExistence(timeout: 8))
        attach("06-record-detail-en")
        app.tabBars.buttons["Profile"].tap(); app.buttons["settings.language"].tap(); app.buttons["简体中文"].tap()
        app.tabBars.buttons["记录"].tap(); attach("07-record-detail-zh")
        app.terminate(); app = launch(large: true)
        XCTAssertTrue(app.tabBars.buttons["记录"].waitForExistence(timeout: 15)); app.tabBars.buttons["记录"].tap()
        app.buttons["records.kind"].tap(); app.buttons["餐食"].tap()
        let largeRow = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH 'meal.record.'")).firstMatch
        reveal(largeRow, in: app); largeRow.tap(); attach("08-record-large-zh")
        app.swipeUp(); attach("09-record-large-zh-lower")
        app.terminate()
    }
    @MainActor func test05PreservedDemoPreview() throws {
        continueAfterFailure = false
        let app = XCUIApplication(); app.launch()
        if app.textFields["login.username"].waitForExistence(timeout: 3) {
            let env = ProcessInfo.processInfo.environment
            app.textFields["login.username"].tap()
            app.textFields["login.username"].typeText(try XCTUnwrap(env["SENPLATE_TEST_USERNAME"]) + "\n")
            app.secureTextFields["login.password"].typeText(try XCTUnwrap(env["SENPLATE_TEST_PASSWORD"]) + "\n")
        }
        if app.buttons["account.open"].waitForExistence(timeout: 3) {
            app.buttons["account.open"].tap(); app.buttons["context.personal"].tap()
        }
        let profile = app.tabBars.buttons.matching(NSPredicate(format: "label == 'Profile' OR label == '我的'")).firstMatch
        XCTAssertTrue(profile.waitForExistence(timeout: 15)); profile.tap()
        app.buttons["settings.language"].tap(); app.buttons["English"].tap()
        app.tabBars.buttons["Records"].tap()
        XCTAssertTrue(app.buttons.containing(.staticText, identifier: "#003").firstMatch.waitForExistence(timeout: 12))
        attach("10-preserved-original-orders")
        app.tabBars.buttons["Home"].tap()
        XCTAssertTrue(app.buttons["meal.connect"].waitForExistence(timeout: 8))
        attach("11-home-with-meal-entry")
    }
    private func simulatedWeight(_ grams: Int) async throws {
        let session = URLSession(configuration: .ephemeral)
        defer { session.invalidateAndCancel() }
        func call(_ path: String, _ body: [String: Any]? = nil) async throws -> [String: Any] {
            var request = URLRequest(url: URL(string: "http://127.0.0.1:8800" + path)!)
            if let body {
                request.httpMethod = "POST"; request.httpBody = try JSONSerialization.data(withJSONObject: body)
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                if let key = body["client_operation_id"] as? String { request.setValue(key, forHTTPHeaderField: "Idempotency-Key") }
            }
            let (data, response) = try await session.data(for: request)
            XCTAssertEqual((response as? HTTPURLResponse)?.statusCode, 200)
            return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        }
        _ = try await call("/v1/device-console/session", ["setup_key": try XCTUnwrap(ProcessInfo.processInfo.environment["SENPLATE_TEST_CONSOLE_KEY"])])
        let current = try await call("/v1/device-console/active")
        _ = try await call("/v1/device-console/simulate", ["client_operation_id": UUID().uuidString,
                       "run_id": try XCTUnwrap(current["run_id"]), "action": "set", "weight_g": grams])
    }
    private func attach(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot()); attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
}
