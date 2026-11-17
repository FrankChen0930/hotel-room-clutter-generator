# Hotel Room Clutter Generation — Common Core V1.0 整合決策摘要（待確認）

日期：2026-11-11

## 0. 依據與證據界線

本摘要依據：

- Codex 的 `Common_Core_V1_Codex_Audit_2026-11-11.md`（Repository、Gap Analysis、現有路徑與歷史證據核對）。
- Claude 的 `Common_Core_V1_Claude_Independent_Review_2026-11-11.md`（架構獨立審查，含原始碼局部核對）。
- Hotel 705 Room-scale 已報告成果：3 支撐面、11 類資產、6 場景、24 圖片、95 件物件的支撐射線歷史 PASS，4 組有限 PhysX PASS。

此摘要本身**不是新執行的驗證**，不可替代原始 run manifest、實測結果、USD 或原始程式。

## 1. 共同結論

採用「資料優先、薄核心、垂直切片」：保留已驗證的 USD overlay、採樣與幾何函式、相對引用、資產 SHA、Manifest Replay、負向測試、有限 PhysX 及 Toolkit 交付機制；不把兩套原有房型生成流程直接包在一個 CLI 裡冒充 Common Core，也不為美觀全面重寫。

主要新增功能是依 **Room Profile × Scenario × Clutter Level × Seed** 形成可重現的物件請求與擺放結果，不再使用 Seed 查表選擇預先寫死的場景配方。

## 2. 建議先決定的 M0 規格（可作預設提案，正式以 Human 核准為準）

| 主題 | 建議決策 | 不做的事情 |
|---|---|---|
| Codebase 位置 | 在 `C:\hotel_room` 下設獨立 Common Core 程式範圍；讀取兩房為不可變依賴，先 pin 實際來源與 SHA | 不遷移／覆寫 YAZHI 原始 USD、Hotel Release、Toolkit 或歷史 Runs |
| Seed／Level／Scenario | Scenario 決定使用情境與物件資格，Level 決定亂度分布目標，Seed 僅決定抽樣；穩定 request ID 對應獨立 RNG stream | 不再用 `seed - 706` 取手寫清單；不把換 Seed 當換 Level |
| 配置資料 | 小型 `RoomProfile`、`Catalog`、`ScenarioLevelPolicy`，加上獨立版本化輸出契約 | 不建立通用 predicate DSL、插件框架或任意 USD 自動語意辨識 |
| Manifest | `schema_version` 明確，唯一權威的 before/after/effective state 與 scene identity；存 evidence references、attempt lineage identifiers，詳細日誌保留於附檔 | 不把全部物理時間序列塞入單一巨大 JSON，也不改寫舊證據 |
| Physics scope | 每個 asset state 描述 physics_proxy 能力；`STATIC_ONLY` 合法；每次動態資格只涵蓋指定 source、support、pose、runtime、collider | 不把支撐 Ray、Static 或局部 PhysX 推定成 95 物件／整房合格 |
| S0 | 先比較已採用的枕頭、毛巾／固定 Mesh 形態；優先選可在平面支撐上展示至少兩種可辨識形態的類別，毛巾為首選候選 | 不要求 V1.0 實作真實 Cloth；不預先將未接受 Mesh 視為通過 |
| 授權 | Catalog 保留來源／授權欄位；內部研究和公開再散布分開審查 | 不因內部測試成功就宣稱資產可公開轉交 |

## 3. 最小架構

`RoomProfile + Asset Catalog + Scenario/Level Policy` → `Planner` → `Placer (sampling + geometry + bounded repair)` → `USD Writer / Manifest / Replay` → `Validators (Static / Support Query / Visual / Limited PhysX / Tamper)`；CLI 僅為操作入口。Room Adapter 只處理 prim、支撐面、座標與來源差異；physics validation 或修正回饋不應改寫既有 run，而是產生新的 attempt 與 lineage。模組邊界是職責，不代表一定要建立同樣數量的新 Python package。

## 4. 建議 Roadmap（階段性驗收，非固定時程）

| 階段 | 目標與交付 | 驗收門檻 |
|---|---|---|
| M0: 基線與契約決策 | 選定程式承載位置，固定兩房來源與 hash；建立最小配置／Manifest 草案，列出既有 PASS 的嚴格 scope；做 YAZHI support primitive 的小型檢查 | 重要 source of truth、schema 欄位、是否只讀依賴一致；無原始檔修改 |
| M1: Hotel 垂直切片 | Hotel 705 使用 RoomProfile/Catalog/Policy，新的 Planner 以 Scenario、Level、Seed 產生 requests；保留已驗證 overlay/Replay；最薄 `generate` CLI | 一間房至少兩情境、三亂度、固定 Seed 能重產；Seed 不再當配方索引；負向測試通過 |
| M2: YAZHI Adapter | 針對 YAZHI primitive/mesh 支撐代理提供薄 Adapter；共用同一 Planner、Writer、CLI | 同一入口可在兩間房生成；核心無兩房專名／世界位置常數；原始 USD hash 不變 |
| M3: 多樣性與亂度品質 | 亂度 Level 獨立控制 count、coverage、分散度／形態；必要時加入地板安全區；高密度可行率 Spike；有界 rejection 保留無解紀錄 | 同房同情境下三亂度有可解釋差異；target 與 actual 記錄，不能無聲退化或刪物；Seed 可重現 |
| M4: S0 形態 | 至少一類軟性資產兩種可辨形態，記錄 state_id、SHA、支撐 envelope，能選取及 Replay | 形態、擺放、Visual/Static 均經驗收；未通過的形態不得標為 accepted；真實 Cloth 非前置條件 |
| M5: 有限物理與修正 | 擴充 physics_proxy 路徑、代表性 dynamic case，將失敗分類／有限修正／新 attempt lineage 接入 | 有可修復與不可修復案例；retry 上限有界；至少代表性多物件與兩種支撐類型通過所宣稱的動態層級；非合格項標明 STATIC_ONLY/NOT_RUN |
| M6: 交付工具化 | CLI 補齊 batch、replay、validate、preflight；版本、資產與出錯診斷；README／範例／週報 evidence link | 不同 CWD、新路徑（含空格）可生成；來源與 Manifest 篡改檢查；不得依賴特定機器寫死路徑 |
| M7: 正式驗收 | 2 房 × 2 Scenario × 3 Levels × 3 Seeds = 36 個獨立案例，代表性有限 PhysX、圖片與交付測試 | 每 case 有 USD、Manifest、Static、Support、Replay、Image/Visual（標明審查者）、適用物理 scope；一案失敗可追蹤；可交給另一研究者依文件試跑 |

M4 可在 M1 Catalog 契約確定後並行；M5 的可行性 spike 可提早進行，但不能因此阻塞 M1–M3。M6 的 CLI 外殼從 M1 就有，M6 只做完整交付封裝。

## 5. 對 Claude 建議的保留與修正

1. **採納**：先 Hotel 垂直切片再接 YAZHI；Toolkit 交付殼 + Hotel 支撐面方法；先定義 Seed/Level；早期薄 CLI；不建立大而全 Solver / LLM。
2. **修正**：代表性整房全 dynamic 可作實驗，不直接列為 V1.0 PASS 必要條件。目前 physics worker 有 Cube-only 限制，其他資產沒有動態 qualification；應採資格明確的動態子集，逐步擴大。
3. **修正**：`Manifest v3` 是權威狀態契約和 evidence 索引，不要求所有大型軌跡與 debug data 寫在同一 JSON。
4. **修正**：毛巾是 S0 優先候選，不在查證已接受的 state／授權前先排除既有枕頭資產。
5. **修正**：跨機 bitwise 物理一致性可以延後，但「其他研究者可在新目錄／新環境依文件執行」是 V1.0 可移交性要求，不能一概標為 OPTIONAL。
6. **修正**：PhyScensis 論文 Appendix A.4.5 明確提到 Genesis 作為物理引擎；其 sample-based Spatial Solver 有 convex-hull penalty + parameter optimization，與現有 bounded rejection sampling 並非同一演算法。參考：https://arxiv.org/html/2602.14968v1

## 6. 初始驗收設計原則

- 把 `RECORDED_PASS` 與本輪重新執行的 `EXECUTED_PASS` 分開。
- 固定 Code/Room/Asset/Profile/Scenario/Level/Seed 才可談可重現；不同版本需另做 compatibility 判定。
- `Requested` 和 `Achieved` Clutter 要各自報告；Level 的「目標」至少符合低、中、高的單調趨勢，但不得以超出容限的失敗案例冒稱完成。
- `Support Ray` ≠ Footprint support ≠ Dynamics；Visualizer image review ≠ Human acceptance。
- 異常狀態 `FAILED`、`NOT_RUN`、`STATIC_ONLY`、`UNKNOWN` 要可識別，不能合併成 PASS。
- 交付再散布限制與內部可執行性分開管理。

## 7. Research Issues 不阻塞 V1.0

- S1：真實布料／枕頭動態形變與烘焙形態保存。
- PhyScensis solver：當高密度可行率確實不足，再比較 OBB、convex hull、occupancy-grid、物理迭代。
- 生成結果自然度、情境可辨識度、物理穩定性指標與 A/B 研究價值。
- 機器人決策、Reward、RL、S2 動態抓布作為方向 B 後續，不成為 Core 的強制依賴。

## 8. 下一步

交由 Codex 以本摘要 + 原始 Codex Audit + Claude Review 編製一份 **正式、可執行且可分階段恢復** 的 Development Roadmap（只規劃不實作）。各 Milestone 列明：前置依賴、明確檔案／模組範圍、交付物、精確分層驗收、風險與回退方案、READY／SPIKE／RESEARCH_REQUIRED 等。Human 確認 Roadmap 後再授權連續自主開發，不安排第三輪全面架構盤點。
