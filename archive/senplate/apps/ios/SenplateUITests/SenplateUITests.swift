import XCTest

final class SenplateUITests: XCTestCase {
    @MainActor func testVerifiedBatchAndLargeText() throws {
        continueAfterFailure = false
        let app = XCUIApplication(); app.launch()
        if app.textFields["login.username"].waitForExistence(timeout: 3) {
            let env = ProcessInfo.processInfo.environment
            app.textFields["login.username"].tap()
            app.textFields["login.username"].typeText(try XCTUnwrap(env["SENPLATE_TEST_USERNAME"]) + "\n")
            app.secureTextFields["login.password"].typeText(try XCTUnwrap(env["SENPLATE_TEST_PASSWORD"]) + "\n")
        }
        XCTAssertTrue(app.buttons["account.open"].waitForExistence(timeout: 15))
        if app.staticTexts["总览"].exists { setLanguage(app, value: "English", done: "Done") }
        XCTAssertTrue(app.staticTexts["station.weight"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["station.weight"].label.contains("1,700"))
        attach("04-verified-overview")
        app.tabBars.buttons["Tasks"].tap()
        XCTAssertTrue(app.buttons["Closed"].waitForExistence(timeout: 5))
        app.buttons["Closed"].tap()
        XCTAssertTrue(app.staticTexts["Completed"].waitForExistence(timeout: 5))
        attach("05-completed-batch")
        app.terminate(); app.launchArguments = ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]; app.launch()
        XCTAssertTrue(app.buttons["account.open"].waitForExistence(timeout: 15))
        XCTAssertTrue(app.staticTexts["station.weight"].waitForExistence(timeout: 10))
        attach("06-large-text-top")
        app.swipeUp(); attach("07-large-text-lower")
        app.tabBars.buttons["Tasks"].tap()
        XCTAssertTrue(app.navigationBars["Tasks"].exists)
        app.terminate(); app.launchArguments = []; app.launch()
        XCTAssertTrue(app.buttons["account.open"].waitForExistence(timeout: 15))
    }
    @MainActor func testEnglishChinesePersistenceAndKitchenFlow() throws {
        continueAfterFailure = false
        let env = ProcessInfo.processInfo.environment
        let username = try XCTUnwrap(env["SENPLATE_TEST_USERNAME"])
        let password = try XCTUnwrap(env["SENPLATE_TEST_PASSWORD"])
        let app = XCUIApplication(); app.launch()
        if app.buttons["account.open"].waitForExistence(timeout: 3) {
            app.buttons["account.open"].tap()
            let logout = app.buttons.matching(NSPredicate(format: "label == 'Sign out' OR label == '退出登录'")).firstMatch
            if !logout.isHittable { app.swipeUp() }; logout.tap()
        }
        let usernameField = app.textFields["login.username"]
        XCTAssertTrue(usernameField.waitForExistence(timeout: 12))
        usernameField.tap(); usernameField.typeText(username + "\n")
        let passwordField = app.secureTextFields["login.password"]
        passwordField.typeText(password + "\n")
        XCTAssertTrue(app.buttons["account.open"].waitForExistence(timeout: 15))
        if app.staticTexts["总览"].exists { setLanguage(app, value: "English", done: "Done") }
        XCTAssertTrue(app.staticTexts["Overview"].firstMatch.exists)
        XCTAssertTrue(app.staticTexts["station.weight"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["station.weight"].label.contains("700"))
        attach("01-overview-en")
        setLanguage(app, value: "简体中文", done: "完成")
        XCTAssertTrue(app.staticTexts["总览"].firstMatch.waitForExistence(timeout: 5))
        attach("02-overview-zh")
        app.terminate(); app.launch()
        XCTAssertTrue(app.staticTexts["总览"].firstMatch.waitForExistence(timeout: 12))
        setLanguage(app, value: "English", done: "Done")
        let suggestion = app.buttons["View suggestion"]
        if !suggestion.isHittable { app.swipeUp() }
        XCTAssertTrue(suggestion.waitForExistence(timeout: 5)); suggestion.tap()
        app.buttons["Accept suggestion"].tap()
        let tasksTab = app.tabBars.buttons["Tasks"]
        XCTAssertTrue(tasksTab.waitForExistence(timeout: 5)); tasksTab.tap()
        let task = app.buttons.containing(.staticText, identifier: "1,000 g").firstMatch
        XCTAssertTrue(task.waitForExistence(timeout: 10)); task.tap()
        for action in ["Start preparation", "Mark ready", "Begin refill"] {
            let button = app.buttons[action]
            XCTAssertTrue(button.waitForExistence(timeout: 5)); if !button.isHittable { app.swipeUp() }; button.tap()
        }
        XCTAssertTrue(app.staticTexts["Waiting for a new, valid weight increase."].waitForExistence(timeout: 5))
        attach("03-awaiting-measurement")
        app.buttons["Done"].tap()
        app.tabBars.buttons["Live"].tap()
        XCTAssertTrue(app.staticTexts["station.weight"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["station.weight"].label.contains("700"))
        app.tabBars.buttons["Overview"].tap()
    }
    @MainActor private func setLanguage(_ app: XCUIApplication, value: String, done: String) {
        app.buttons["account.open"].tap()
        let picker = app.buttons["settings.language"]
        XCTAssertTrue(picker.waitForExistence(timeout: 5)); picker.tap()
        app.buttons[value].tap()
        app.buttons[done].tap()
    }
    private func attach(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
}
