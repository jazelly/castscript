// castscript menu bar app: runs `castscript web` in the background and opens its page from a menu bar icon.
// `castscript app` compiles this file into castscript.app and writes the server command into Resources.
import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    let resources = Bundle.main.resourceURL!
    var statusItem: NSStatusItem!
    var server: Process?
    var url: URL!

    func applicationDidFinishLaunching(_ notification: Notification) {
        url = URL(string: try! String(contentsOf: resources.appendingPathComponent("url"), encoding: .utf8)
            .trimmingCharacters(in: .whitespacesAndNewlines))!
        startServer()

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        let icon = NSImage(contentsOf: resources.appendingPathComponent("menubar.svg"))!
        icon.size = NSSize(width: 18, height: 18)
        icon.isTemplate = true
        statusItem.button!.image = icon
        statusItem.button!.toolTip = "castscript"

        let menu = NSMenu()
        menu.addItem(withTitle: "Open castscript", action: #selector(openPage), keyEquivalent: "o")
        menu.addItem(withTitle: "Show Server Log", action: #selector(openLog), keyEquivalent: "l")
        menu.addItem(.separator())
        menu.addItem(withTitle: "Quit castscript", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        statusItem.menu = menu
    }

    var logURL: URL { FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/castscript-web.log") }

    func startServer() {
        let command = try! String(contentsOf: resources.appendingPathComponent("command"), encoding: .utf8)
            .split(separator: "\n").map(String.init)
        FileManager.default.createFile(atPath: logURL.path, contents: nil)
        let log = try! FileHandle(forWritingTo: logURL)
        let process = Process()
        process.executableURL = URL(fileURLWithPath: command[0])
        process.arguments = Array(command.dropFirst())
        // Engines call ffmpeg; GUI apps do not inherit the shell PATH.
        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + (env["PATH"] ?? "/usr/bin:/bin")
        process.environment = env
        process.standardOutput = log
        process.standardError = log
        try! process.run()
        server = process
    }

    @objc func openPage() { NSWorkspace.shared.open(url) }
    @objc func openLog() { NSWorkspace.shared.open(logURL) }

    func applicationWillTerminate(_ notification: Notification) { server?.terminate() }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
