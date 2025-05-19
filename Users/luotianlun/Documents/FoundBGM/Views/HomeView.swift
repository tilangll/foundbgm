import SwiftUI
import PhotosUI
import UIKit  // 添加这行

struct HomeView: View {
    @State private var selectedImage: UIImage?  // 改回 UIImage
    @State private var selectedImageItem: PhotosPickerItem?
    @State private var selectedMusicType = MusicType.all
    @State private var inputText = ""
    @State private var showingResult = false
    
    enum MusicType: String, CaseIterable {
        case all = "全部音乐"
        case instrumental = "纯音乐"
        case vocal = "带歌词音乐"
    }
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    if let image = selectedImage {
                        Image(uiImage: image)  // 改回 uiImage
                            .resizable()
                            .scaledToFit()
                            .frame(maxHeight: 300)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            .overlay(
                                Button(action: { selectedImage = nil }) {
                                    Image(systemName: "xmark.circle.fill")
                                        .foregroundStyle(.white)
                                        .font(.title)
                                }
                                .padding(8),
                                alignment: .topTrailing
                            )
                    } else {
                        PhotosPicker(selection: $selectedImageItem,
                                   matching: .images) {
                            VStack(spacing: 12) {
                                Image(systemName: "photo.badge.plus")
                                    .font(.largeTitle)
                                Text("选择图片")
                                    .font(.headline)
                            }
                            .frame(maxWidth: .infinity)
                            .frame(height: 200)
                            .background(Color(.systemGray6))  // 改回 UIKit 的颜色引用
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                    }
                    
                    // 音乐类型选择
                    VStack(alignment: .leading, spacing: 8) {
                        Text("音乐类型")
                            .font(.headline)
                        Picker("音乐类型", selection: $selectedMusicType) {
                            ForEach(MusicType.allCases, id: \.self) { type in
                                Text(type.rawValue).tag(type)
                            }
                        }
                        .pickerStyle(.segmented)
                    }
                    .padding(.horizontal)
                    
                    // 文本输入
                    VStack(alignment: .leading, spacing: 8) {
                        Text("文案（选填）")
                            .font(.headline)
                        TextEditor(text: $inputText)
                            .frame(height: 100)
                            .padding(8)
                            .background(Color(.systemGray6))  // 改回 UIKit 的颜色引用
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                    .padding(.horizontal)
                    
                    // 匹配按钮
                    Button(action: startMatching) {
                        if showingResult {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        } else {
                            Text("开始匹配")
                                .font(.headline)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .background(selectedImage != nil ? Color.blue : Color.gray)
                    .foregroundColor(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(.horizontal)
                    .disabled(selectedImage == nil || showingResult)
                }
                .padding(.vertical)
            }
            .navigationTitle("BGM 匹配助手")
        }
        .onChange(of: selectedImageItem) { newItem in
            Task {
                if let data = try? await newItem?.loadTransferable(type: Data.self),
                   let image = UIImage(data: data) {
                    selectedImage = image
                }
            }
        }
    }
    
    private func startMatching() {
        guard let image = selectedImage else { return }
        showingResult = true
        // TODO: 实现匹配逻辑
    }
}

#Preview {
    HomeView()
}