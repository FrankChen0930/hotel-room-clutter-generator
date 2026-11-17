# Common Core V1.0 — Local RC 交接

目前工程已完成 WU-00～WU-21。WU-22 的程式包、操作文件與作者重現已就緒；**獨立研究者操作尚未完成，不宣告 V1_HANDOFF_ACCEPTED**。

依據原 Roadmap A14／WU-22，必須由另一研究者實際完成兩房指定案例、replay 與 validate，作者不能代簽。這項要求不影響已完成的工程驗收。

## 可核對的結果

- 正式 36 案：Static、Support、Visual、Replay、Integrity 全部通過。
- 原生 Support：6,236 個採樣點通過。
- 視覺：實際檢視 178 張原圖／補圖，選用 131 張；不可用與 UNKNOWN 視圖保留。Agent review，Human acceptance 待驗。
- 正式代表性動態：兩房各 book＋can 雙物件，240 步／120 Hz，Mesh／Cube 支撐幾何，所有目標檢查與程序 exit 通過；只適用精確指定物件、場景、姿態與 runtime。
- 舊 Hotel 六案重新重建通過；13 類資格失效／篡改負向檢查通過，包含實際修改圖片副本後被拒絕。
- 92 項自動測試通過；後續驗收只在確認核心與測試逐檔雜湊完全相同時重用該紀錄。每個 WU 另有實際專屬驗收。
- 最終程式包在新含空格位置、不同 CWD、實際來源重新綁定後，兩房指定案例重生成／replay／validate 通過，與正式 state digest 相同。這是作者重現，不能替代獨立操作。

本地程式版本：`e6e5c22`，完整 Commit 與逐檔清單見移交證據。沒有 Push、發布、額外付費 API 或原始來源修改。

## 移交位置

- 程式來源：`C:/hotel_room/common_core`
- 最終程式包：`C:/hotel_room/_common_core_runs/work_units/WU-22/a000/final code delivery/Common Core code`
- 完整移交索引：`C:/hotel_room/_common_core_runs/work_units/WU-22/a000/final_delivery_index.json`
- 套件逐檔雜湊／來源授權範圍：同一 `final code delivery` 目錄的 `inventory.json`、`external-rights.json`
- 作者最終重現：`C:/hotel_room/_common_core_runs/work_units/WU-22/a000/author final repro/author-repro.json`
- 正式 36 案：`C:/hotel_room/_common_core_runs/work_units/WU-20/a000/formal36`
- 各 WU 收據、版本、失敗嘗試與原生紀錄：`C:/hotel_room/_common_core_runs/work_units`

程式包不包含原始 USD、貼圖、外部 Repository、歷史證據或 SDK。外部來源須由操作者合法取得並保持唯讀。內部測試用來源副本保存在 WU-18 證據範圍，與程式包分開。

## 獨立研究者實際操作

先閱讀程式包內 `docs/QUICK_START.md`。可將已驗證的本機 deployment 複製成自己的新設定檔；也可以依 `config/deployment.example.json` 綁定自己合法取得的來源。保留 profile／catalog／policy／source lock，不更新雜湊來略過錯誤。

由真正的另一位研究者在 PowerShell 執行（填入自己的姓名；輸出必須是新目錄）：

```powershell
$py = 'C:/isaac_sim/kit/python/python.exe'
$core = 'C:/hotel_room/_common_core_runs/work_units/WU-22/a000/final code delivery/Common Core code'
$base = 'C:/hotel_room/_common_core_runs/work_units/WU-22/a000'
Copy-Item -LiteralPath "$base/remounted.local.json" -Destination "$base/researcher.local.json"
& $py -B "$core/tools/researcher_handoff.py" --operator '實際獨立研究者姓名' --independent-operator --config "$base/researcher.local.json" --reference-index "$base/final_delivery_index.json" --output 'C:/hotel_room/_common_core_runs/independent researcher handoff 20261114'
```

若設定檔或輸出已存在，改用新檔名／目錄，不覆寫既有證據。工具會實際執行：

1. Hotel705／STAYOVER／low／706 的重生成、replay、validate。
2. YAZHI／CHECKOUT／medium／707 的重生成、replay、validate。
3. 比較兩案正式 state digest，保存操作者宣告、環境、命令、exit、log SHA 與 `researcher-receipt.json`。

操作完成後，提供該 receipt 的本機路徑與實際操作者身分，再由接收者核對。作者不會代填姓名或冒充另一研究者執行。僅有作者測試或工具 `--help` 不算 A14 通過。

## 版本與回退

只在新 `common_core` 範圍使用本地 Git；沒有其他 Repository 修改或遠端 Push。另有保留實際檔案位元組的 code-only ZIP 與 SHA。需要精確重現既有 state digest 時，使用已驗證 ZIP 與 inventory 還原相同位元組，再綁定來源；Git 換行轉換可能改變以實際位元組計算的 code hash。

## 尚待完成的驗收

WU-22 保留 `LOCAL_RC_COMPLETE / INDEPENDENT_OPERATOR_REQUIRED`。在獨立操作收據與操作者獲核對前，Delivery Reproducibility 層仍保留待驗，不把整個 V1.0 標為正式交接接受。單一 Active Plan 持續保存在原位置，沒有另開計畫。
