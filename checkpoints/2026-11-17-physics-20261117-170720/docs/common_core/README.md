# Common Core V1.0 規劃入口

狀態：**APPROVED_D01_2026-11-14 / IMPLEMENTATION_IN_PROGRESS**。
原規劃日期：2026-11-11；D-01 核准日：2026-11-14。此目錄是規劃與進度的唯一位置；實際完成的程式、測試、版本與證據見單一 Active Plan 及 progress.md。

## 閱讀順序與權威範圍

1. [最終功能規格](Common_Core_V1_Functional_Spec.md)：V1 必達、排除範圍、分層結果與完成門檻。
2. [架構與資料契約草案](Common_Core_V1_Architecture_Contracts.md)：資料流、模組、狀態權威、介面、路徑與版本。
3. [正式 Development Roadmap](Common_Core_V1_Development_Roadmap.md)：M0–M7、Dependency Map、Work Unit Backlog、驗收、風險／Research Issues、自主開發與第一個工作單元。
4. [單一活躍計畫](.planning/2026-11-11-common-core-v1/task_plan.md)：只記執行位置與 milestone 狀態，不複製另一份 Roadmap。

規格決定「需要達成什麼」；架構文件決定「資料與介面如何對接」；Roadmap 決定「工作順序與驗收」。工作進度以 task_plan.md 與 progress.md 為準，不能把文件寫完視為 M0–M7 已實作。

## 已讀輸入與優先順序

優先序：使用者 D-01 核准與補充 → 已採用的功能規格／契約／Roadmap → 整合決策摘要 → 兩份審查的相容結論。原審查文件中的「待確認」是歷史狀態；不再逐單元要求方向確認，也不啟動第三輪全面盤點。

| 輸入文件 | 本輪讀取時 SHA256 |
|---|---|
| [Codex Audit](Common_Core_V1_Codex_Audit_2026-11-11.md) | `4218edffe27a5fd298e014bab00a959dd8c95a12559899f3b333f67440ac290a` |
| [Claude Independent Review](Common_Core_V1_Claude_Independent_Review_2026-11-11.md) | `94475f343ed80e502e83047f6ae192ce8b424ed30ae7a910c1025a338709cae8` |
| [Integrated Decision Brief](Common_Core_V1_Integrated_Decision_Brief_2026-11-11.md) | `d8de7d28e503b08fb6fb2b10ec6abc58fec8042230a49584314fa22f40fa2380` |

三份皆存在，保留原文。它們記載的 PASS 一律為歷史 RECORDED_PASS，本次沒有重跑 287 檔案盤點、36 案例、渲染或 PhysX。

## 本次一次確認涵蓋的預設方向

- 未來程式放 `C:/hotel_room/common_core/`，新 runs／實驗／交付放 `C:/hotel_room/_common_core_runs/`；既有兩房型、Toolkit 及歷史 Run 是唯讀依賴。
- Hotel 垂直切片 → YAZHI 第二房型；Planner 真正由 Scenario／Level 產生 requests，Seed 只控制抽樣。
- 家具預設固定；S0 先評估毛巾兩形態，不合適時改用已採用的枕頭兩形態；無須再為此普通選型停工。
- 36 案例逐層驗收，加代表性有限動態；不要求全部物件／整房動態。
- 方向確認後由 Codex 依 backlog 連續開發、測試、修復與記錄；不預設付費 API、子 Agent 或每單元人工批准。

**停止點：本次只交付計畫；收到 Human 對整體方向的明確確認後，才可開始 WU-00。** 未回覆、逾時或文件初始化不代表核准。

> D-01 approved 2026-11-14: [binding execution supplement](D-01_Approval_2026-11-14.md) supersedes historical planning-only, no-local-commit and per-scene S0 wording. Execution state is maintained in the single Active Plan.
