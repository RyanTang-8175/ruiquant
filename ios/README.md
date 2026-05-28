# RuiQuant iOS App

## 在 Xcode 中打开

### 方法一：创建新项目（推荐）

1. 打开 Xcode
2. 选择 "Create a new Xcode project"
3. 选择 "iOS" → "App"
4. 填写信息：
   - Product Name: `RuiQuant`
   - Organization Identifier: `com.ruiquant`
   - Interface: `SwiftUI`
   - Language: `Swift`
5. 选择保存位置：`/Users/7yq/vibe coding项目/股票/ios/`
6. 创建完成后，删除自动生成的 `ContentView.swift` 和 `RuiQuantApp.swift`
7. 把 `ios/RuiQuant/` 下的文件拖入 Xcode 项目
8. 修改 `ContentView.swift` 中的 `streamlitURL` 为你的 Mac IP

### 方法二：直接打开

1. 在终端运行：
```bash
cd /Users/7yq/vibe\ coding项目/股票/ios
open -a Xcode .
```

2. 如果提示需要项目文件，按方法一创建

## 运行前准备

1. **启动 Streamlit 服务器**
```bash
cd /Users/7yq/vibe\ coding项目/股票
source venv/bin/activate
streamlit run app.py
```

2. **获取 Mac IP 地址**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

3. **修改 ContentView.swift**
   - 找到 `let streamlitURL = "http://localhost:8501"`
   - 改为 `let streamlitURL = "http://你的MacIP:8501"`

4. **iPhone 连接**
   - iPhone 和 Mac 在同一 WiFi
   - iPhone 用数据线连接 Mac
   - 在 Xcode 中选择你的 iPhone 作为运行目标

## 运行

1. 在 Xcode 中点击 ▶️ 运行按钮
2. App 会安装到你的 iPhone 上
3. 打开 App，看到 Streamlit 页面

## 注意事项

- 免费 Apple ID 每 7 天需要重新签名
- 重新签名：在 Xcode 中重新运行即可
- 如果连接失败，检查：
  - Streamlit 是否在运行
  - iPhone 和 Mac 是否在同一网络
  - IP 地址是否正确
