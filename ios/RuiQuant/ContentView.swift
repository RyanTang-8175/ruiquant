import SwiftUI
import WebKit

struct ContentView: View {
    @State private var isLoading = true
    @State private var errorMessage: String? = nil

    // Streamlit 服务器地址（改成你的 Mac IP）
    let streamlitURL = "http://localhost:8501"

    var body: some View {
        ZStack {
            // 背景色
            Color(red: 0.05, green: 0.07, blue: 0.09)
                .ignoresSafeArea()

            if let error = errorMessage {
                // 错误页面
                VStack(spacing: 20) {
                    Image(systemName: "wifi.slash")
                        .font(.system(size: 60))
                        .foregroundColor(.red)

                    Text("连接失败")
                        .font(.title)
                        .foregroundColor(.white)

                    Text(error)
                        .font(.body)
                        .foregroundColor(.gray)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)

                    Button("重试") {
                        errorMessage = nil
                        isLoading = true
                    }
                    .padding()
                    .background(Color.red)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                }
            } else {
                // WebView
                WebView(url: streamlitURL, isLoading: $isLoading, errorMessage: $errorMessage)
                    .ignoresSafeArea()

                // 加载指示器
                if isLoading {
                    VStack {
                        Spacer()
                        HStack {
                            Spacer()
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .red))
                                .scaleEffect(1.5)
                            Spacer()
                        }
                        Spacer()
                    }
                    .background(Color.black.opacity(0.5))
                }
            }
        }
    }
}

// WebView 组件
struct WebView: UIViewRepresentable {
    let url: String
    @Binding var isLoading: Bool
    @Binding var errorMessage: String?

    func makeUIView(context: Context) -> WKWebView {
        let webView = WKWebView()
        webView.navigationDelegate = context.coordinator
        webView.scrollView.bounces = false
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0.05, green: 0.07, blue: 0.09, alpha: 1)

        if let url = URL(string: url) {
            let request = URLRequest(url: url)
            webView.load(request)
        }

        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, WKNavigationDelegate {
        var parent: WebView

        init(_ parent: WebView) {
            self.parent = parent
        }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            parent.isLoading = true
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            parent.isLoading = false
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            parent.isLoading = false
            parent.errorMessage = "加载失败: \(error.localizedDescription)"
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            parent.isLoading = false
            parent.errorMessage = "无法连接到服务器\n请确保 Streamlit 正在运行\n\n\(error.localizedDescription)"
        }
    }
}

#Preview {
    ContentView()
}
