# Senplate 字体商用许可核查

核查日期：2026-09-18。范围：当前 Logo 与 VI 字体；不包含新一轮图形商标清查。

## 结论

当前 Logo 的实际字体为 **Manrope Bold，字重700**，Figma 可编辑字标保留-2%字距。Manrope、Noto Sans TC、Noto Sans SC 均采用 SIL Open Font License 1.1，可免费用于商业Logo、网站、App、印刷及其他设计作品。早期对照标注使用的Inter也采用OFL 1.1，但不是本套VI的主字体。

| 字体 | 本项目用途 | 官方许可 |
|---|---|---|
| Manrope | Logo字标；VI英文及数字排版 | [Google Fonts仓库OFL](https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/OFL.txt) |
| Noto Sans TC | 繁体应用模板和字体体系 | [官方OFL](https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/OFL.txt) |
| Noto Sans SC | 简体规范文档和字体体系 | [官方OFL](https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/OFL.txt) |
| Inter | 历史对照标注，当前VI不依赖其字体文件 | [作者仓库许可](https://raw.githubusercontent.com/rsms/inter/master/LICENSE.txt) |

OFL官方FAQ明确允许将字体用于Logo、图形及制造物，无须额外许可；使用字体制作的作品不因此被要求按OFL发布。[OFL FAQ 1.1、1.1.1、1.13](https://openfontlicense.org/ofl-faq/)

## 使用与分发条件

- 商业设计使用无需另付字体许可费，也不要求在Logo旁标注字体作者。
- 再分发字体文件时保留版权说明与完整OFL，不单独出售字体文件。
- 若修改字体软件，需要遵守OFL及适用的保留字体名称条款；这与使用现有字体制作Logo不同。

本套已附当前三种字体的原始可变TTF、OFL、官方元数据；Manrope另附FONTLOG。Inter只附已核查的许可副本。文件来源、下载时间和SHA-256存于素材包 `05_Fonts_and_Licences/provenance.json`。核对时这些原件字节未改变。

用于PDF嵌入的静态实例仅在本轮QA目录生成，不作为独立字体再分发。生产Logo及应用SVG已转轮廓；`06_Source/wordmark-editable.svg`保留文字，编辑前安装所附Manrope字体。

这是字体许可结论，不把它表述为Senplate名称或碗形商标已注册／完成法律清查。
