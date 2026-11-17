## 1. Executive Summary

目前已有足以建立 Common Core V1.0 的工程基礎，但尚未形成兩房型共用的生成核心。 主要工作是統一資料契約、抽離房型設定、整合既有幾何與驗證工具，再補上亂度控制、有限失敗修正及跨房型驗收；沒有證據顯示必須重寫全部生成演算法。

最大優勢是既有成果具備來源雜湊、相對 USD overlay、Manifest、重播、負向測試，以及有限 PhysX 原生執行證據。主要缺口是：

- YAZHI、Hotel 705 與 Toolkit 仍有不同的資料結構、入口與房型假設。
- 三段亂度只存在於 Hotel 705 原始 Release 生成器，尚未接入最新 Scenario 流程。
- 幾何拒絕取樣已有有界重試；物理失敗後的自動診斷、修正與重試閉環尚未完成。
- S0 離散形態已有實作，但跨房型放置、接觸代理及驗收規則仍需整理。
- 尚未執行 Common Core 的 36 案例矩陣，也未完成跨機重現驗收。

最新 Hotel 705 Room-scale 已實際核對，沒有停留在 Seed 705。

| 項目 | 本輪核對結果 |
|---|---|
| 正式批次 | roomscale_20261111T115831030089Z |
| 場景 | Seeds 706–708 × STAYOVER／CHECKOUT，共 6 場景 |
| 物件數 | STAYOVER：9／10／12；CHECKOUT：18／21／25，合計 95 |
| 支撐面／種類 | 3 個支撐面，11 類物件 |
| 圖片 | 24 筆實際渲染圖片紀錄 |
| 分層結果 | 六場景均有 Static、Visual、Manifest Replay、Support Ray 歷史 PASS |
| PhysX | 四個具名有限配置，均有 PASS_LIMITED_CASE、240 steps／120 Hz、native exit 0 |
| 證據完整性 | 本輪重算 artifact_index.json 所列 287 個檔案 SHA256，全部吻合 |
| 身分一致性 | 六場景 Visual 的 scene／manifest hash 均吻合；generator／adapter hash 亦吻合 |

上述為 RECORDED_PASS，加上本輪檔案完整性查證，不是本輪重新執行生成、渲染或物理驗收。Visual 是歷史 assistant 圖像審查；不是人工量測確認。95 個支撐射線也不代表完整接觸或動態穩定性驗收。

本輪未修改程式、USD、Manifest、歷史 Run 或管理文件。

## 2. Repository / Source of Truth Map

以下路徑均以 C:\hotel_room 為根。

| 範圍 | 真實位置與入口 | 版本／可信度與用途 |
|---|---|---|
| YAZHI 原始建模 | YAZHI-TWIN/room/usd/YAZHI_TWIN.usd；tracking/spec_registry.yaml；scripts/correct_mapping.py | 房型 v2.3 audit-mapped correction。Registry 是建模事實來源；不是 clutter policy |
| YAZHI 建模證據 | YAZHI-TWIN/reports/handoff.json、reports/mapping_v2_3/、reports/mapping_runtime/ | 保存建模 Visual／Static／PhysX regression 歷史結果；本輪未重驗 |
| YAZHI 研究 Generator | YAZHI-TWIN/experiments/phase_v2_room_clutter/ | Generator v2 與房型 v2.3 是不同版本軸；後續研究分布於多個實驗目錄 |
| YAZHI task 基線 | housekeeping_policy/，再到 housekeeping_realism/、task_quality/ | Seed49 配對情境與選擇性外觀改善；最新候選不等於 adopted |
| YAZHI 有限物理流程 | scenario_pipeline/pipeline.py、new_seed_bridge/ | 精確來源／資產／支撐／姿態資格管理；不是任意新配置的物理證書 |
| Hotel 705 原始 Release | _hotel705_reference/release_v1.0.0/hotel705-random-clutter/ | 7052 ver3／Release v1.0.0。原始 generator.py 自成一套流程 |
| Hotel 705 Seed705 Pilot | _hotel705_pilot/pilot.py、room_profile.json、active_run.txt | 兩件物件、一個桌面；保留早期成功與失敗證據 |
| Hotel 705 最新 Room-scale | _hotel705_pilot/roomscale/；active_batch.json、active_cases.json | 本次 Hotel 成果的主要查詢入口；報告與逐 Run 證據相符 |
| Toolkit 程式 checkout | _yazhi_randomizer_staging/p52_gitprep/hotel-room-clutter-generator/ | 0.1.0-rc.1-internal；39 tracked files；本輪 Git clean |
| Toolkit 最新交付證據 | p52_gitprep/p52_assetpub_20261106T122437Z/ | 記錄私人 prerelease、資產 ZIP、fresh-download QA；比 checkout README 的發布描述更新 |
| Toolkit 早期候選／QA | run_20261106T0652280738737Z/、p35_*、p5prep_*/release-candidate/ 等 | 封裝歷程與重定位測試副本，不能全部視為 active source |
| 早期房間檔案 | yazhi_fullroom/ | 有 Blender／USD 檔案；未找到它取代 YAZHI v2.3 的依據 |
| 週報與簡報 | presentation/lab-slides/、presentation/2026-11-12/ | 展示與證據副本，不是 Generator 或資產真實來源 |

### Git 狀態

| 位置 | 本輪觀察 |
|---|---|
| workspace root、YAZHI、Pilot、Hotel Release、yazhi_fullroom、presentation root | Git metadata MISSING |
| Toolkit checkout | branch main，HEAD 92d171937b517cd3a32b2a5ecfd48a83a4dec2ff；clean；39 tracked files；一個 worktree；本地無 tag |
| Toolkit p52_assetpub_*/tag.git | bare repo；v0.1.0-rc.1-internal 指向同一 commit |
| presentation/lab-slides | master 尚無 commit；38 個 index 檔案，包含既存 staged／modified 狀態及未追蹤週報 |
| 其他 worktree | 在本輪限定的程式／交付目錄 metadata 探查中未發現 |

Git 最初因執行帳號與擁有者不同拒絕查詢；後續只使用單次命令的 safe.directory 參數，未修改全域設定。

發布狀態的時間差必須保留： Toolkit README 與早期 Final QA 仍寫「未發布」，但後續 Final Delivery Summary (/C:/hotel_room/_yazhi_randomizer_staging/p52_gitprep/p52_assetpub_20261106T122437Z/FINAL_DELIVERY_SUMMARY.md) 記錄私人 prerelease 已發布、fresh-download QA 30 cases／92 checks 通過。這是歷史發布證據；本輪未連線重新確認私人遠端現況。

## 3. Architecture & Data Flow

### YAZHI／Toolkit 流程

Canonical USD + 房型設定 + Asset Lock
  → discover：家具群組、collider、原始 world transform
  → furniture：固定候選區域內取樣、桌椅距離／朝向
  → task_plan：CHECKOUT／STAYOVER recipe、ownership、soft state
  → prop_plan：support／間距／碰撞近似拒絕取樣
  → derive + bedding：相對 reference overlay
  → scene_manifest + dependency_manifest
  → static readback／同 Seed 比較／Manifest Replay

Toolkit 的實際呼叫鏈為：

toolkit/randomize.py:main
→ runtime_support.configure/bootstrap/check_assets
→ vendor/generate.discover
→ vendor/iterate.furniture
→ vendor/task_helpers.task_plan
→ iterate.derive、task_helpers.bedding
→ runtime_support.validate_scene。

研究版另有：

scenario_pipeline/pipeline.py
→ qualification gate
→ adapter prepare
→ native worker
→ runtime reset／replay
→ measured final USD／Manifest。

Toolkit 刻意沒有接上這條物理鏈，且會拒絕 --physics qualified。

### Hotel 705 Room-scale 流程

Release 房間 USD
  → prepare.py：三個指定支撐面的 mesh triangles／障礙物
  → adapter.json：支撐面、YAZHI locked assets、原生 amenities
  → recipe(seed, scenario)：物件種類、數量、預期支撐面、姿態
  → generate：有界取樣與支撐面 fallback
  → author：原房間 sublayer + 新增 reference／amenity override
  → manifest.json
  → validate：Static + 依 Manifest 重建 replay
  → render／record_visual
  → native support rays
  → prepare_cases／physics：四個有限配置
  → deliver：報告與證據索引

| 階段 | 主要函式／格式 | 硬編碼與耦合 |
|---|---|---|
| Room Input | Toolkit common.ROOM/PREFIX；Hotel inspect_source.SOURCE、prepare.ROOM | 分別固定 /YAZHI_TWIN 與 /root、房間路徑及 sibling layout |
| Room／Support Mapping | YAZHI discover()；Hotel top_triangles() | YAZHI 依家具名稱、Shell prefix；Hotel 固定 desk／minibar／bench prim |
| Asset Selection | Toolkit asset_states.json、asset_lock.json；Hotel adapter.json | Hotel preparation 仍讀早期 staging 的 rigid_assets_source.json，再取 YAZHI 原樹資產 |
| Scenario | task_plan()；Hotel recipe()、semantic() | 兩套 enum／欄位及語意策略；Hotel recipe 以 seed-706 選三組 pattern |
| Sampling／Constraints | furniture_checks/prop_plan/pair/contains；Hotel height/support_ok/obstacle_hit | YAZHI 有固定世界座標、床中心與 support paths；Hotel mug flip／tea PCA 是資產特例 |
| USD Output | derive/bedding/author/set_world | 依 OpenUSD；生成以 reference／sublayer 保留來源，需整個依賴閉包 |
| Validation | Toolkit validate_scene()；Hotel validate()、raycheck.py | 多個檢查依賴 assertion；不能用 optimized Python 靜默跳過 |
| Replay | Toolkit saved manifest restore；Hotel author(replay, manifest) | 是不重抽樣重建；Hotel 重播仍使用同一個 author，不是另一套獨立 writer |

重要邊界：

- YAZHI registry 不直接等於生成器 Room Profile。 家具候選區、keep-out、recipe 多為研究設定。
- YAZHI 幾何以 upright Circle／OBB primitive 為主；Hotel 以水平 mesh top、AABB 與局部 triangle bounds 為主，不能直接互換。
- Hotel 取樣每物件最多 2400 次，在 800／1600 次切換支撐面；有記錄 requested／actual support 與 attempts。
- Hotel validate() 名稱雖為 verify，但會寫 static.json、replay USD／JSON；本輪沒有執行它。
- 調整 namespace、transform 次序、資產尺度、支撐面、碰撞代理、物理參數或 Manifest schema，都可能破壞既有重播或精確資格比對。

## 4. Existing Capability Matrix

OBSERVED_IMPLEMENTED 表示本輪讀到實際程式；RECORDED_PASS 表示已有歷史證據，兩者可以並存。

| 功能 | 狀態 | 已確認範圍與限制 |
|---|---|---|
| Scene Import／來源保留 | OBSERVED_IMPLEMENTED、RECORDED_PASS | 兩房均有相對 overlay；通用 room loader／profile contract 為 PARTIAL |
| 固定家具／可動物件控制 | OBSERVED_IMPLEMENTED、PARTIAL | YAZHI 有 mobility policy、joint 排除；Hotel 有 amenity override whitelist。尚無共用控制模型 |
| 支撐／允許區／禁止區 | OBSERVED_IMPLEMENTED、PARTIAL | 既有 support、keep-out、障礙物檢查可用；仍綁定房型，未涵蓋任意斜面、凹面或全房通行性 |
| Asset Pool | OBSERVED_IMPLEMENTED、RECORDED_PASS、PARTIAL | 有 ID、版本、來源、尺寸、SHA、collider、部分 profile／證據；尚未統一原生 amenity 與外部資產 |
| Scenario | OBSERVED_IMPLEMENTED、RECORDED_PASS | YAZHI／Toolkit 及 Hotel 均有兩情境；策略不同，尚未統一 |
| Clutter Level | OBSERVED_IMPLEMENTED、PARTIAL | Hotel 原始 Release 有 low／medium／high；最新 Room-scale 與 Toolkit 缺獨立亂度控制 |
| Generation／Sampling | OBSERVED_IMPLEMENTED、RECORDED_PASS | 有 Seed、bounded rejection、幾何約束、部分 fallback；不是通用關係 solver |
| PhysX／Failure Handling | OBSERVED_IMPLEMENTED、RECORDED_PASS、PARTIAL | 有 contact／trajectory／velocity／native exit 與精確資格；缺自動物理修正閉環 |
| Scene State／Manifest／Replay | OBSERVED_IMPLEMENTED、RECORDED_PASS、PARTIAL | 有 final poses、資產與來源身分、重建；原始狀態與 effective state 分散在不同檔案 |
| Static／Visual／Dynamic | OBSERVED_IMPLEMENTED、RECORDED_PASS | 分層紀錄清楚；各層不能互相替代，完整房間動態未驗收 |
| S0 多形態 | OBSERVED_IMPLEMENTED、PARTIAL | 有 Neat／Compressed Pillow、SideDrape 等固定 mesh states；仍 VISUAL_ONLY，跨房型接入未完成 |
| Batch／CLI／Packaging | OBSERVED_IMPLEMENTED、RECORDED_PASS、PARTIAL | Toolkit CLI 較成熟；Hotel 固定六場景 batch；兩房統一入口 MISSING |
| 跨機重現／36 案例 | NOT_VERIFIED | 既有交付明列 cross-machine NOT_RUN；本輪亦未執行 |
| 部分研究候選 | FAIL／未採用 | Gathered clearance 約 0.30 mm，低於原 0.50 mm 門檻；reference bedding 為 DO_NOT_ADOPT |
| Blender cylinder 診斷 | FAIL | 約 1.47 mm 對 0.20 mm 門檻 NOT_MET；不等同推翻 static USD QA |

### 驗證範圍的精確界線

- Hotel Static：所選支撐面上的保守包圍盒、角點、1 mm gap、障礙物分離與 override whitelist；不是整房 mesh narrow-phase。
- Support Ray：每物件以 observed bounds 中心發出向下射線，過濾生成物件後確認原生 collider；不是整個 footprint 的接觸面積或 COM 穩定性證據。
- Hotel PhysX：四個案例中，桌面的 Tissue、Book＋Tissue 使用原 Seed705 Pilot 姿態；新 minibar／bench 各取一個已視覺接受姿態。
- 四案例均在 unsaved session 凍結其他剛體並停用原房間 31 joints；未驗收整房關節或全部 95 物件。
- 原兩物件案例的 FAIL／exit1 保留；後續修正的是 enclosing AABB 誤判，沒有換場景姿態後冒稱原配置通過。

## 5. Common Core V1.0 Gap Matrix

為保留可讀性，以下兩表以 R1–R12 對應同一組需求。證據代號見第 10 節。

### 現況、來源與重用

| ID／Requirement | Current Implementation | Evidence | Status | Reusable Components |
|---|---|---|---|---|
| R1 匯入 USD、保留來源階層 | reference／sublayer overlay 已有 | E2、E4 | OBSERVED_IMPLEMENTED／RECORDED_PASS | relative paths、dependency closure、world transform |
| R2 至少兩房型 | 兩房資料與各自流程存在，共用 profile 缺失 | E2–E4 | PARTIAL | YAZHI discovery、Hotel adapter |
| R3 物件、支撐與區域管理 | mobility、keep-out、support、override whitelist 分散存在 | E3、E5、E6 | PARTIAL | 幾何檢查、原始矩陣、mobility policy |
| R4 原生及外部 Asset Pool | manifest／lock／profile／amenity metadata 分散 | E3、E8 | PARTIAL | immutable asset IDs、hash、尺寸、來源與 qualification refs |
| R5 CHECKOUT／STAYOVER | 兩套已執行，但語意與 recipe 不同 | E1、E6 | OBSERVED_IMPLEMENTED／RECORDED_PASS | task metadata、policy eligibility |
| R6 低／中／高亂度 | 只在 Hotel 原始 Release 完整列出三段參數 | E12 | PARTIAL | count presets、姿態比例概念 |
| R7 Seed／config／batch | Toolkit 支援 signed32 seed；Hotel 固定 batch | E1、E4 | PARTIAL | RNG、fingerprint、unique run、CLI |
| R8 情境與約束生成姿態／狀態 | 剛體、soft states、局部關係已有 | E2、E5、E6 | PARTIAL | sampler、SAT、support、state selector |
| R9 幾何／物理驗證與有限修正 | 驗證豐富；幾何 retry 已有；物理修正缺失 | E2、E7 | PARTIAL | native worker、contact checks、qualification gate |
| R10 至少一類 S0 多形態 | 枕頭／被褥／毛巾狀態存在 | E6、E9 | PARTIAL | adopted static mesh library、state SHA |
| R11 全狀態與版本／失敗紀錄 | manifests 與 evidence 有，但契約不一致 | E1、E3、E4、E7 | PARTIAL | pose records、dependency hashes、failure receipts |
| R12 統一 CLI／簡單入口 | Toolkit 單房 CLI 成熟；跨房統一入口缺失 | E4 | PARTIAL；共用入口 MISSING | parser、preflight、output guard、error codes |

### Missing Capabilities、Required Changes、Dependency、Risk、Acceptance

| ID | Missing Capabilities／Required Changes | Dependency | Risk | Suggested Acceptance Test |
|---|---|---|---|---|
| R1 | loader 接受 profile 與 source URI；將 units／up-axis 轉換留在 adapter／overlay | R2 | 改變原階層或 transform 意義 | 來源 SHA 不變；非目標 prim／joint 保持；依賴可解析 |
| R2 | 定義小型 Room Profile；建立 YAZHI、Hotel adapter；移出 Prim／座標常數 | 契約決策 | 隱性房型假設漏出 | 同一 CLI 以兩份 profile 生成；core 不含兩房專名 |
| R3 | 統一固定／可動／articulated、support、allowed／forbidden region；未知幾何明確回傳 UNKNOWN | R2 | 過保守拒絕或漏檢 | 禁區、越界、joint 物件、支撐改變的負向測試 |
| R4 | 統一 asset ID／state／version、pivot、尺度、collider、必要物理欄位及 qualification scope | R2、R3 | 視覺與 collider 不一致；錯用資格 | 缺欄位、錯 SHA、尺度／collider 改變能拒絕或降級 |
| R5 | 統一 enum 與 scenario policy；明確允許 left-behind guest item | R4 | 兩套 policy 靜默改變含義 | 同 Seed 配對測試；guest／unknown 不自動轉垃圾 |
| R6 | 亂度獨立於 scenario／seed；定義 count、覆蓋率、分散度、狀態比例及可行上限 | R3–R5 | 高密度飽和；把情境差誤當亂度差 | 每房每情境三段目標成立；不可行時記錄失敗／降級規則 |
| R7 | 共用 batch spec、固定選用資產／profile、獨立 RNG streams、逐案結果 | R2、R5、R6 | 加一物件導致所有 RNG 決策漂移 | 同設定重抽樣一致；saved replay 不採樣；一案失敗不隱藏其他結果 |
| R8 | 統一 placement request／constraint result；將 mug flip 等移到 asset adapter | R3、R4 | 姿態／座標系錯誤 | 支撐移動、旋轉物件、碰撞與無解 fixture |
| R9 | 結構化失敗原因；明確 retry budget；局部重抽樣／換支撐／停止規則 | R8、有限物理 spike | 無限迴圈、靜默刪物、誤擴 qualification | 注入 unsupported／unstable case；修正成功及預算耗盡皆可追溯 |
| R10 | 選定至少一類 accepted S0；記錄 state identity、support envelope 與 collision scope | R2–R4 | 沿用舊 collider 或採用未接受候選 | 至少兩形態可辨識並可 replay；跨目標 support 檢查通過 |
| R11 | 統一 before／after、source→instance mapping、effective state、環境與所有失敗 attempt | 全流程契約 | 多份 manifest 欄位互相矛盾 | 可由輸出包追溯／重建每物件；篡改來源、state、pose、版本必被偵測 |
| R12 | 統一 generate／replay／validate／batch 入口，保留現有實驗入口 | R1–R11 | 封裝時意外 import 舊 main 或繼承舊路徑 | 新資料夾、不同 CWD、含空白路徑完成兩房流程 |

R1–R8、R11–R12 主要是工程整合。R9 的一般化物理回饋、R10 的跨支撐 S0 接觸策略適合小型 spike；不必先解決任意 USD 理解或完整物理 solver。

## 6. Reuse vs Adapt vs Build

| 分類 | 元件 | 整合成本與建議 |
|---|---|---|
| 原樣重用 | Canonical／Release 資產、adopted state USD、歷史 Run／證據 | 以 immutable dependency 使用；不重寫舊 Manifest 或 receipt |
| 重用演算法 | geometry_check 的 Circle／OBB、SAT、support gap；Hotel barycentric height、角點檢查 | 低至中；抽離房型常數，保留 UNKNOWN 與既有限制 |
| 重用交付機制 | Toolkit hash／version／dependency closure、output guard、failure receipt、CLI 結構 | 中；去除單房與固定部署位置假設 |
| 小型 Adapter | YAZHI furniture groups／Shell colliders；Hotel 三支撐面／native amenities | 中；讓差異停留在 room adapter，不滲入共用 sampler |
| 改造 | scenario recipe、clutter parameter、RNG streams、before／after mapping | 中；需新 schema，保留 legacy importer |
| 改造 | qualification classifier、native worker／contact／trajectory 檢查 | 中至高；重用方法與原始證據，不轉移舊 PASS |
| 建立 | 共用 Room Profile、Asset／State contract、Batch spec、Failure result | 必要的薄層，避免建立大型框架 |
| 建立 | bounded repair controller | 先支援少量已知失敗類型；每次修正保存 lineage |
| 暫緩 | LLM Agent、通用 predicate DSL、S1／S2、RL／GUI | 非 V1 必達，沒有成為目前先決條件的理由 |
| 不採用 | Gathered、HybridSideDrape、reference bedding 最新未接受候選 | 保留研究證據，不自動升級成正式 state |

不建議直接搬整條 YAZHI 研究 import chain：既有盤點已指出 adapter/build/generate/prepare 等 bare module names 與 sys.path 次序耦合。Toolkit 的萃取版本可作較乾淨的整合起點，但仍需解除房型常數。

## 7. Technical Risks & Research Questions

### 一般工程風險

- 來源與版本分歧： 多個 staging／QA 副本，以及過期 README。應由明確 commit、asset lock、profile hash 與 active run 指向。
- Manifest 語意分歧： 原始 generator state 與 refined effective state 可同時存在；Common Core 必須指定哪個是最終狀態。
- 部署路徑： USD arcs 多為相對路徑，但 Python、JSON ledger、runtime root 仍有絕對路徑。
- 資產物理資料不完整： mass／尺寸多為 provisional；有 collider 不表示動態合格。
- 既有單房 AGENTS 範圍過時： 它保護 canonical 很有價值，但不能直接充當 Common Core 的多房型工作契約。

### 需要技術 Spike 的假設

1. 水平 support／primitive 近似是否足以涵蓋 V1 的目標放置。
   Hotel 角點落在三角形上，不必然證明跨凹洞的整個 footprint 都受支撐；應用少量凹面／邊緣 fixture 確定限制。
2. 代表性 PhysX 能否接入有限修正。
   先驗證「局部姿態重抽樣／改用允許支撐面」即可；不必先讓所有物件同時自由動態。
3. S0 的可重用支撐表示。
   優先使用既有 Neat／Compressed Pillow 等固定形態，檢查 pivot、底面、碰撞代理是否適用兩房型；不用先解完整布料。

### PhyScensis 相關性

官方方法包含 predicates、sample-based spatial solver、物理求解與失敗回饋迭代；這可作分層設計參考，並不要求本案先導入 LLM。PhyScensis 官方方法說明

| 面向 | 本專案現況 | 判斷 |
|---|---|---|
| Spatial／Physical Predicates | PLACE_ON／FOLDED_ON、桌椅 facing／distance、support／clearance、protected item 等局部函式 | 可重用；目前沒有共用 predicate model |
| Constraint Sampling／Solver | 有界拒絕取樣、幾何檢查、支撐面 fallback | 已有方法；不是通用 solver |
| Physics Feedback | 保存 contact、軌跡、速度、penetration、native errors | 有驗證回饋，尚未自動驅動生成修正 |
| Failure Diagnosis | 有原因欄位、原始 log、保留失敗與人工 root-cause 分析 | PARTIAL；缺統一分類與修正映射 |
| Bounded Retry／Resampling | geometry、pillow、towel 及 Hotel support fallback 已有 | 已實作；物理 retry 仍是明確新 case／人工控制 |
| LLM refinement | 未實作 | V1 不需要 |

本輪在官方 project page、作者頁及論文搜尋中，未確認可直接取得的實作 repo 與程式授權：Code availability／license = UNKNOWN。論文公開不等於程式可直接重用。論文原始頁

可能的碩論問題包括情境可辨識度與物理可行性的權衡、有限回饋修正效率、S0 多形態對場景多樣性的貢獻；這些可延後，不預選方向 A／B。

## 8. Preliminary Milestones

| 順序 | 工作項目／交付 | 標記 |
|---|---|---|
| M0 | 選定 Common Core 程式承載位置、兩房基線、最小 schema 與 qualification 用語 | DECISION_REQUIRED |
| M1 | 建立 Room／Asset／State／Run 契約與兩個 adapter，先保持既有算法 | READY |
| M2 | 整合幾何、overlay、Manifest、Replay，完成兩房薄切片 | READY |
| M3 | 統一兩 Scenario 與三亂度；使 counts／coverage／state 分布可配置 | READY |
| M4 | 評估一類 S0 的兩形態、pivot／support／collider scope | RESEARCH_REQUIRED |
| M5 | 代表性 PhysX＋結構化 failure＋有限修正 spike | RESEARCH_REQUIRED |
| M6 | 統一 CLI／batch／環境與資產鎖定，整合分層結果 | DEPENDENCY_BLOCKED：待 M1–M5 |
| M7 | 執行並審查 36 案例、代表性物理與重定位交付 | DEPENDENCY_BLOCKED：待整合完成 |

### Agent 工作流程評估

五個指定技能均已存在於 YAZHI-TWIN/.agents/skills/，並有 skills-lock.json。本輪採用 codebase-knowledge-builder 的讀碼與證據追蹤方法，其餘技能只檢查適用性，未啟動新計畫或 hooks。

現有 .planning/.active_plan 指向 2026-11-11-hotel705-pilot；該計畫已延伸到 Room-scale，能支援續作。不過早期段落仍寫 Tissue／多物件未驗證，後段才記錄完成，閱讀時容易混淆。

必要調整僅有：

- 未來實作時沿用一個 active plan；不要再建立平行 Roadmap。
- 將舊資格限制加上時間／scope，避免被後續成果錯誤覆蓋。
- 在實際 Common Core 範圍提供相應 AGENTS；保留 YAZHI canonical 的保護規則。
- Research issues 繼續連結既有實驗結果與失敗證據即可；本輪未找到必須另建 issue 管理系統的需求。
- verification-before-completion 應用於新執行結果；歷史結果明列 RECORDED_PASS，避免為了用詞重新跑全部歷史測試。

## 9. Proposed Acceptance Strategy

36 案例驗收應分層執行，不要求 36 次整房動態。

| 驗收層 | 建議範圍與判定 |
|---|---|
| 來源保護 | 兩房輸入與資產 SHA 不變；來源階層、非目標矩陣及 joints 保持 |
| 基本矩陣 | 2 房 × 2 Scenario × 3 Levels × 3 Seeds，共 36 案例；每案獨立輸出與結果 |
| Seed 重現 | 固定 code／profile／assets／config 後，同 Seed 重抽樣比較語意計畫與 pose；另做不採樣的 Manifest Replay |
| 亂度 | 同房同情境下檢查設定的 count／coverage／分散度／state 指標；不能靠換 Seed 冒充三段亂度 |
| 情境 | CHECKOUT／STAYOVER 有明確 recipe／state 差異；guest／unknown 保護規則一致 |
| 幾何與支撐 | 逐物件檢查 footprint、gap、禁止區、物件間距、collider 可用性；UNKNOWN 不計 PASS |
| 視覺 | 固定相機檢查各案例接觸、尺度、穿插及形態；審查結果綁定 scene／manifest／image hashes |
| S0 | 至少一類、兩個可辨識形態；保存 state ID／SHA／pose；檢查目標 support、穿透與 replay |
| 代表性 PhysX | 按資產 collider、支撐類型與姿態挑代表案例，包含多物件；記錄凍結範圍、contact／trajectory／settling／native exit |
| 有限修正 | 至少一個可修復與一個不可修復 fixture；確認 retry 上限、失敗原因與每次 attempt 完整保存 |
| 負向控制 | 錯來源／asset／profile hash、pose tamper、off-support、禁區、未授權 source override、缺依賴 |
| 交付重現 | 新目錄、不同 CWD、含空白路徑，依文件完成 generate／replay／validate；另一研究者環境另列 cross-machine 結果 |

應分別報告 Static、Visual、Support Query、Limited Dynamics、Replay 與完整性，避免單一 PASS 掩蓋範圍。

## 10. Evidence & Uncertainty

### 重要來源與函式

| 代號 | 可獨立審查的來源 |
|---|---|
| E1 | Room-scale validation (/C:/hotel_room/_hotel705_pilot/roomscale/report/validation.json)、weekly report (/C:/hotel_room/_hotel705_pilot/roomscale/report/weekly_report.md)、artifact index (/C:/hotel_room/_hotel705_pilot/roomscale/report/artifact_index.json) |
| E2 | Hotel generate.py (/C:/hotel_room/_hotel705_pilot/roomscale/generate.py:20)：height 20、support_ok 34、author 50、validate 73、recipe 127、generate 145、bounded sampling 182、Manifest 207 |
| E3 | Hotel prepare.py (/C:/hotel_room/_hotel705_pilot/roomscale/prepare.py:14)：top_triangles 14、支撐／資產／amenity mapping 30 起、原始 amenity matrix 96 |
| E4 | Toolkit randomize.py (/C:/hotel_room/_yazhi_randomizer_staging/p52_gitprep/hotel-room-clutter-generator/toolkit/randomize.py:20)、runtime_support.py (/C:/hotel_room/_yazhi_randomizer_staging/p52_gitprep/hotel-room-clutter-generator/toolkit/runtime_support.py:67)：bootstrap 67、closure 84、asset checks 107、fingerprint 124、validate 142 |
| E5 | geometry_check.py (/C:/hotel_room/YAZHI-TWIN/experiments/phase2_geometry/geometry_check.py:45)：primitive extraction 45、pair check 114、support 148；Toolkit iterate.py (/C:/hotel_room/_yazhi_randomizer_staging/p52_gitprep/hotel-room-clutter-generator/toolkit/vendor/iterate.py:31)：固定 destinations 33、support paths 54、床中心 92 |
| E6 | Toolkit task_helpers.py (/C:/hotel_room/_yazhi_randomizer_staging/p52_gitprep/hotel-room-clutter-generator/toolkit/vendor/task_helpers.py:18)：task plan 18、bedding 26；研究版 generate_tasks.py (/C:/hotel_room/YAZHI-TWIN/experiments/phase_v2_room_clutter/housekeeping_policy/generate_tasks.py:18)：height cache、towel／cue sampling |
| E7 | Hotel physics.py (/C:/hotel_room/_hotel705_pilot/roomscale/physics.py:87)：240 steps、case checks、settling；raycheck.py (/C:/hotel_room/_hotel705_pilot/roomscale/raycheck.py:36)：中心射線與結果 scope；YAZHI pipeline.py (/C:/hotel_room/YAZHI-TWIN/experiments/phase_v2_room_clutter/scenario_pipeline/pipeline.py:83)：dispatch 與禁止重複派送 |
| E8 | external asset manifest (/C:/hotel_room/YAZHI-TWIN/experiments/phase2_external_asset_pool/asset_manifest.v1.json)、phase2b3/validated_asset_pool.v1.json；Toolkit asset_states (/C:/hotel_room/_yazhi_randomizer_staging/p52_gitprep/hotel-room-clutter-generator/toolkit/config/asset_states.json) |
| E9 | task_quality README (/C:/hotel_room/YAZHI-TWIN/experiments/phase_v2_room_clutter/task_quality/README.md)、reference_bedding README (/C:/hotel_room/YAZHI-TWIN/experiments/phase_v2_room_clutter/reference_bedding_pilot/README.md)：選擇性採用、門檻未達與 DO_NOT_ADOPT |
| E10 | 私人 Release 最終交付 (/C:/hotel_room/_yazhi_randomizer_staging/p52_gitprep/p52_assetpub_20261106T122437Z/FINAL_DELIVERY_SUMMARY.md)、同目錄 d/qa/acceptance_20261106T123009351418Z/results.json |
| E11 | active task plan (/C:/hotel_room/YAZHI-TWIN/.planning/2026-11-11-hotel705-pilot/task_plan.md)、progress (/C:/hotel_room/YAZHI-TWIN/.planning/2026-11-11-hotel705-pilot/progress.md)、AGENTS (/C:/hotel_room/YAZHI-TWIN/AGENTS.md) |
| E12 | Hotel Release generator.py (/C:/hotel_room/_hotel705_reference/release_v1.0.0/hotel705-random-clutter/generator.py:30)：LEVELS、SURFACES、FLOORS、1200-attempt sampler |
| E13 | 既有 execution map (/C:/hotel_room/YAZHI-TWIN/reports/github_packaging_audit/run_20261106T0627385971543Z/execution_map.md)、capability matrix (/C:/hotel_room/YAZHI-TWIN/reports/github_packaging_audit/run_20261106T0627385971543Z/capability_matrix.md)：本輪增量盤點基礎 |

### 本輪查證與未查明事項

- 已重算 Room-scale 索引 287 個檔案雜湊，核對六場景的狀態、24 圖片紀錄、95 ray checks、四組 native exit，以及保留的原兩物件 FAIL。
- 已讀取實際呼叫鏈與關鍵函式；未執行專案生成／verify／preflight 入口，避免其寫檔副作用。
- 本機直接讀到 C:\isaac_sim\VERSION = 6.0.0-rc.59+release.41464.5f2772bc.gl；C:\isaac_sim\python.bat 存在，所查 D:\isaacsim 不存在。
- nvidia-smi 回報 RTX 5070 Ti Laptop GPU、12227 MiB、driver 592.00。未進行效能測試；後續容量規劃應依這個實際配置。
- YAZHI／Hotel 全部歷史證據、原始 ZIP 與全部資產未重新全面驗證；61 個 Pilot／150 個 YAZHI 保護結果仍屬歷史紀錄。
- 私人遠端現況、跨機重現、任意 Seed 成功率、高亂度可行率、未測物件動態及 S0 跨房型接觸仍為 NOT_VERIFIED。
- PhyScensis 程式與授權為 UNKNOWN。
- 未追蹤大型資產、快取、browser profiles 或敏感內容；presentation 的技能 junction 已標為排除，未循連結掃描。
- Toolkit 最終仍 Git clean；presentation 保留既存狀態。本輪沒有寫入、commit、merge、push、部署或啟動 Common Core 實作。