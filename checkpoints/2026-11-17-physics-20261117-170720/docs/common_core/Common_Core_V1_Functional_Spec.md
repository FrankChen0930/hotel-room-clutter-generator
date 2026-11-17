# Common Core V1.0 最終功能規格

版本：規劃版 1.0，2026-11-11。狀態：APPROVED_D01_2026-11-14。
目標產品：**Reproducible, Scenario-Conditioned Physical Scene Generator**。
依據：[整合決策](Common_Core_V1_Integrated_Decision_Brief_2026-11-11.md) §1–6；輸入身分與衝突優先序見 [README](README.md)。本文件已由 D-01 核准為正式功能範圍；核准不等於功能已實作完成。

## 1. 使用情境與邊界

研究者提供已標註 Room Profile、Asset Catalog、Scenario/Level Policy 及 Seed，以同一入口生成保留來源階層的 USD overlay、權威狀態 Manifest 與可追溯驗證。支援 Hotel 7052 ver3 與 YAZHI v2.3 兩份獨立房型。允許人工標註，無任意 USD 自動語意理解承諾。

V1 預設房殼、家具、床組及原有關節固定；允許移動 profile 白名單內的原生 amenities，並新增外部資產。保存 YAZHI 舊家具搬移功能／證據，但移植該功能不在關鍵路徑。原生物件搬移須移動其完整視覺／碰撞階層，不能只動 mesh。

來源：`YAZHI-TWIN/room/usd/YAZHI_TWIN.usd`、`_hotel705_reference/release_v1.0.0/hotel705-random-clutter/assets/room7052/7052_ver3_0925.usda`。實際 hash／依賴集合於 WU-00 精確 pin，不能只靠檔名或報告版本。

## 2. 功能與可測結果

| ID | 必達功能 | 完成條件／主要工作單元 |
|---|---|---|
| F01 | 匯入房間並保留來源與階層 | 相對 sublayer/reference overlay；來源檔案 SHA 不變，非白名單 prim／joint 不變；WU-00/05/07 |
| F02 | 兩房型使用同一核心 | Profile 與 adapter 可含房型 path；Planner/Placer/Writer 不含兩房專名或世界位置；WU-03/07/08 |
| F03 | 物件控制與約束 | 固定／可動／articulated 分開；support、允許區、禁止區、來源 override 白名單皆有資料與負向測試；WU-02/03/07 |
| F04 | 原生與外部 Asset Catalog | ID／version／state／SHA／尺寸與來源／pivot／對齊／collider／物理能力／授權範圍可追溯；WU-01/03/11/13 |
| F05 | CHECKOUT、STAYOVER | 情境控制資格、ownership、狀態與組成；明列 synthetic assumptions；guest／unknown 不自動成垃圾；WU-04 |
| F06 | low、medium、high | Level 控制數量、coverage 目標、分散及形態比例；與 Seed、Scenario 分離；WU-04/09/10 |
| F07 | Seed／配置／batch | signed32 Seed；穩定 request ID 與明確 RNG 派生；固定版本可重產；逐案輸出；WU-01/04/17 |
| F08 | 受約束位置、姿態及狀態 | 允許 support／pose／state 內有界抽樣；保留 requested/achieved 與拒絕原因；WU-04/05/09/15 |
| F09 | 分層驗證及有限修正 | Geometry、Support、Visual、Replay、Integrity 與代表性 PhysX 分開；可修復／不可修復案例與新 attempt lineage；WU-05/06/14/15/16 |
| F10 | S0 一類至少兩形態 | 同類兩個不同 mesh/state SHA 可辨識、兩房平面支撐可使用、可 replay；WU-11/12 |
| F11 | 狀態與證據保存 | 唯一 before/after/effective state、identity mapping、環境／資產／code 版本、evidence refs、失敗原因與 attempts；WU-01/05/15/18/19 |
| F12 | 研究者入口與交付 | preflight/generate/replay/validate/batch；不同 CWD、新路徑含空白；另一研究者依文件完成小樣本；WU-05/17/18/22 |

## 3. Seed、Scenario、Level 的規範

- Scenario 決定可用類別、ownership、狀態資格與計數組成；Level 選擇數量／coverage／分散／形態分布目標；Seed 不決定 Level、不索引手寫場景。
- 同一 room/scenario/seed 的 count 目標滿足 low < medium < high。以非重疊整數區間及同一 count quantile 實作；不要求不同 Level 的所有物件 pose 完全相同。
- 穩定 ID：`<role>/<asset-family>/<ordinal>`；不使用目前 list index 或 USD 遍歷次序。`sha256` 派生 RNG，禁止 Python 內建 `hash()` 或全域 RNG 狀態。
- 新增無關 request 不改變既有 request 的抽樣亂數流；碰撞約束可能導致既有 request 改 pose，必須誠實記錄，不能承諾整場佈局完全不變。
- 初始 count 提案（含新增物件與被移動原生物件，不重複計算未動原生物件；S0 算一件）：

| Scenario | low | medium | high |
|---|---:|---:|---:|
| STAYOVER | 5–6 | 8–9 | 12–13 |
| CHECKOUT | 7–8 | 11–12 | 16–18 |

這些是新工程政策提案，不是審查已驗證數字。M1 先用上述區間；M3 以固定 calibration seeds 7001/7002/7003、兩房可用面積及資產實際 footprint 校準，輸出版本化 policy 和範圍變更原因。不得在 M7 看見失敗後改門檻或替換 Seed 求過關。校準可由 Codex 自行執行；若連最低功能範圍都不可行才升級方向決策。

Coverage 定義為固定允許支撐面上的投影 footprint 聯集面積／同一可用面積，近似量測方法、網格解析度與 area mask 必須版本化。每房／Scenario 的 denominator 跨 Level 相同；不得靠臨時加大 floor denominator 美化指標。M3 凍結每房／Scenario／Level 的 achieved coverage 容許區間，並要求三 Seed 平均 coverage 嚴格遞增。分散度記錄 occupied-support count 與 normalized centroid spread；形態記錄 state／lying 比例。M3 至少一項分散或形態目標隨 Level 改變且達成，不能只增加同款物件數。

Count／required categories 是硬約束。Coverage／分散／state 的硬或軟門檻逐欄位寫入 policy；軟指標仍須報 target/actual，但不偽裝成達標。最終 36 案例必須符合凍結的所有硬門檻。失敗不能靜默刪物、降 Level、換 Seed 或沿用舊 PASS。

## 4. S0、物理能力與修正

S0 是靜態多形態資產，不需要 runtime Cloth。優先評估已採用毛巾在平面支撐的兩形態；若既有形態僅在 duvet 投影情境有效，先比較 Neat/Compressed Pillow 等已採用資產。選型可在已確認內部使用範圍內自主完成；不預先採用 Gathered、Hybrid 或標 DO_NOT_ADOPT 的候選。

兩形態須保留兩房與專門 8 案的 Static/Support/Visual/Replay 驗收；36 個正式案例不強制每案放置 S0，由 Scenario/Level Policy 決定。仍須證明兩形態在兩房與兩種 Scenario 下可正常使用，每房每 Scenario 的九個 Level/Seed 組合中兩形態至少各出現一次。state change 不等於 yaw change。S0 的非物理 proxy 合法，但不得繼承舊床品 collider 的動態資格。

生成預設 kinematic/static；未測物件為 STATIC_ONLY 或 NOT_RUN。Catalog 的 physics_proxy 只描述能力，不賦予 qualification。代表性動態最低覆蓋兩房、至少兩種支撐幾何類型，以及至少一例同時兩個 dynamic bodies。只涵蓋被測 asset state／collider／source／support／pose／runtime／參數；其餘物件保持凍結並記錄。整房全動態不是 V1 硬門檻。

有限修正依序：同 support 重抽樣 → policy 允許的其他 support → policy 允許的其他 pose。禁止為通過而移除 required request；optional request 省略必有理由，且不滿足 Level 硬目標時整案仍 FAILED。物理初試後最多一次修正後 native retry；新 scene/new attempt，不覆寫原失敗。runtime crash、缺依賴、權限問題不自動偽裝成幾何失敗重抽樣。

## 5. 結果與完成定義

| 層 | 必要證據 | 不可推論 |
|---|---|---|
| Static / Geometry | 實際 composed pose、footprint／gap／碰撞近似、禁區與 whitelist、scope | 不能推論 native dynamics／完整 mesh narrow phase |
| Support Query | 原生 collider query，預期 prim／hit／位置、查詢模式與容差 | 射線不能替代 footprint 或 COM 穩定性 |
| Visual | 真實 render、固定相機／設定、圖片 SHA、審查者／時間／結論 | agent review 不是 human acceptance 或真實尺寸量測 |
| Manifest Replay | 不採樣重建、composed state／pose 比較、依賴與 state 身分 | 不要求另寫第二套 writer，不推論 runtime replay |
| Limited Dynamic Physics | contact／trajectory／settling、native steps/dt/exit、測試與凍結範圍 | 不繼承為其他 Seed／pose／source 的資格 |
| Source / Asset Integrity | source closure／catalog／policy／code hashes、原檔保護 | 不能用檔名、mtime 或 README 代替內容身分 |
| Delivery Reproducibility | 新目錄／CWD 與另一研究者重生成 receipt | 不要求跨機 bitwise PhysX 一致 |

結果分開記錄 `execution=NOT_RUN|EXECUTED|RECORDED`、`outcome=PASS|FAIL|UNKNOWN|NOT_APPLICABLE`、scope 與 rationale。`STATIC_ONLY` 是 asset/state 能力，不能偽裝成動態 PASS；歷史 RECORDED_PASS 不計作新 Common Core 案例 EXECUTED_PASS。

正式完成需：36 個固定鍵案例全部通過適用硬門檻；每案包含 USD、Manifest、Static、Support、Replay、Image/Visual、Integrity、動態 scope 狀態；代表性物理／修正測試通過；交付文件及另一研究者的小樣本重現通過。若研究者尚未試跑，可稱 LOCAL_RC_COMPLETE，不能稱 V1_HANDOFF_ACCEPTED。Human 的可用時間只影響最後 handoff，不阻擋其他 READY 工程。

## 6. 非必達與權限

不納入：任意 USD 自動理解、通用 Solver／predicate DSL／plugin framework、LLM Agent、S1 真實柔性、S2 操作、RL／Reward、完整 GUI、必須重設所有算法、完整房間動態資格。保留未解研究問題，不預選碩論 A/B。

Catalog 保存來源、授權及內部／公開再散布限制。開發與當前內部環境測試不以公開授權查明為前置；對外提供受限資產必須另有足夠授權，否則採 code-only＋研究者合法取得的 dependencies。Human 未允許前不自動邀請、發信、上傳、發布、commit 或 push。

> D-01 approved 2026-11-14: [binding execution supplement](D-01_Approval_2026-11-14.md) supersedes historical planning-only, no-local-commit and per-scene S0 wording. Execution state is maintained in the single Active Plan.
