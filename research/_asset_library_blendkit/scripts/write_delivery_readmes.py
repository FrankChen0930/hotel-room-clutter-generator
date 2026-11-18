"""Write bilingual project entrypoints only from freshly verified actual results."""
import argparse
from pathlib import Path
from library import ROOT,read,write,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkout',type=Path,required=True);p.add_argument('--local-run',type=Path,required=True);p.add_argument('--public-run',type=Path,required=True);p.add_argument('--download',default='downloads/hotel705_examples.zip');a=p.parse_args()
    checkout=a.checkout.resolve();assert checkout.is_relative_to(ROOT.parent/'_project_delivery')
    for run in [a.local_run,a.public_run]:assert read(run/'verification.json')['outcome']=='PASS'
    status=read(ROOT/'reports/status.json');local=read(a.local_run/'scene_quality_summary.json')['cases'];public=read(a.public_run/'scene_quality_summary.json')['cases']
    assert len(local)==len(public)==6
    for row in local+public:assert row['physics']=='PASS' and row['visual_review']=='PASS'
    download=checkout/a.download;assert download.is_file() and download.stat().st_size<95*1024*1024
    remote='https://github.com/FrankChen0930/hotel-room-clutter-generator'
    stats=f"{status['local_technical_ready']}";variants=status['local_qualified_variants']
    table='\n'.join(f"| {c['seed']} | {c['level'].capitalize()} | {c['count']} | PASS | [Preview](docs/previews/public-{c['level']}{c['seed']}.png) | `scenes/{c['level']}_seed_{c['seed']}.usda` |" for c in public)
    gallery='''| Low | Medium | High |
| --- | --- | --- |
| ![Low](docs/previews/library-low706.png) | ![Medium](docs/previews/library-medium706.png) | ![High](docs/previews/library-high706.png) |
'''
    command=r'& "C:\isaac_sim\kit\python\python.exe" -B research\_asset_library_blendkit\scripts\run_public_workflow.py --tag my_hotel705_run --seeds 706 707'
    english=f'''# Hotel Room Clutter Generator

**English** | [繁體中文](README.zh-TW.md)

Seeded hotel guest clutter, measured placement surfaces, full-room rigid simulation and portable USD examples. Research progress for **19 November 2026**.

**Randomization scope: guest clutter only.** The original bed, desk, cabinet and chair layout is retained. Simulation of authored room bodies/joints is separate from furniture-layout randomization, which is not implemented here.

![Hotel705 — expanded local library](docs/previews/library-high706.png)

The image shows the **local research pool**. The downloadable examples use the original Hotel705 props with confirmed room redistribution permission; their smaller prop pool is shown separately below. Blendkit models are not included in the download.

{gallery}
## Current results

- **{stats} independently counted Blendkit assets locally accepted**, plus {variants} appearance variants counted separately. Conversion, actual Isaac images, visual review, Static/Integrity/Native Support/Replay are checked; downloads and instances are not usable-asset counts.
- Two seeds (**706 / 707**) × three density ranges: **Low 10–20**, **Medium 30–50**, **High 70–80** object instances.
- Every delivered scene has an actual **30 s / 120 Hz / 3,600-step CPU PhysX** room test, including the original room bodies and joints. Final-two-second stability, displacement, support-region retention, dependencies and effective-pose replay are checked for these exact cases.
- Soft-body deformation is deferred. Fixed-form geometry and approximate rigid proxies do not qualify cloth manipulation, calibrated masses or arbitrary future seeds.

## Download ready-to-open rooms

[**Download clean room + six example scenes**]({remote}/raw/refs/heads/main/{a.download}) · [Package checksums](docs/PACKAGE_STATUS.json)

Extract the complete ZIP and keep its `assets/` folder. Open `clean_room.usda` for the unmodified room arrangement, or choose a scene below. Normal scenes retain the settled generated poses; `_dynamic.usda` variants activate the tested rigid setup. An isolated USD file without its dependencies is insufficient.

![Public native-prop example](docs/previews/public-high706.png)

**Public examples use five original-room prop records with limited diversity and repeated instances.** They are independent from the expanded Blendkit research pool and do not increase its asset count. Source/permission and exact package mappings are recorded in the archive.

| Seed | Level | Instances | Room physics | Preview | Path inside ZIP |
| --- | --- | ---: | --- | --- | --- |
{table}

## Reproduce room → generation → physics → USD

The repository includes permission-audited room/native input data and a separate public runtime under `research/`. The existing `toolkit/` is retained.

Tested on Windows, Isaac Sim **6.0.0-rc.59**, its bundled Python and an RTX5070Ti Laptop GPU. Rendering uses Direct3D12; dynamics use CPU PhysX. Other SDK versions are not certified. Use the bundled Isaac Python; change its executable path for your installation.

```powershell
{command}
```

This samples both seeds and all levels, runs bounded simulation feedback, exports settled/dynamic USD, verifies scoped source hashes/physics/Replay/dependencies, and captures actual images. Results go to new directories under `research/_asset_library_blendkit/runs/`. Use a fresh tag each time. No Blendkit login, subscription or model-download API is used by this public example workflow.

```mermaid
flowchart LR
  R[Room + permitted props] --> P[Seed / level / measured supports]
  P --> C[Static and dependency checks]
  C --> S[Whole-room rigid simulation]
  S -->|Failed, bounded resampling| P
  S -->|Pass| U[Settled USD + dynamic USD]
  U --> V[Manifest / Replay / native images]
```

## Asset and rights scopes

`docs/asset_sources.json` records original Blendkit IDs, authors, source URLs, versions, source SHA and separate rights gates. Free acquisition or local technical acceptance does not clear extractable-USD redistribution. Blendkit GENERATION_READY/public Starter remain {status['generation_ready']}/{status['public_starter']}; these counts do not describe the separately permitted original-room examples.

Hotel705 room/native redistribution permission was confirmed by the project maintainer on18November2026. No blanket license is assigned to third-party material. See [rights](RIGHTS.md), [license status](LICENSE_STATUS.md) and [delivery scope](docs/DELIVERY_SCOPE.md). The original room attribution is retained. Raw Blendkit models, textures, add-on, profiles, credentials, SDK and paper PDFs are excluded.

This is research evidence for the included cases, not a robot-safety or universal dynamics certificate.
'''
    chinese=f'''# Hotel Room Clutter Generator

[English](README.md) | **繁體中文**

以 Seed 生成飯店住客雜物，結合實測擺放區域、全房間剛體模擬與可攜式 USD。**2026/11/19 研究進度**。

**目前隨機化的是住客雜物，主要家具配置固定。** 床、桌、櫃、椅保留原始布局；原場景剛體／關節參與模擬，不代表已實作家具重新配置。

![Hotel705 本機擴充資產場景](docs/previews/library-high706.png)

上圖使用**本機研究資產池**。公開下載範例使用已確認房間散布同意的 Hotel705 原生道具，種類較少；下載包不含 Blendkit 模型。

{gallery}
## 目前成果

- **{stats} 種獨立 Blendkit 資產通過本機驗收**，另有 {variants} 個外觀變體分開記錄。完成轉換、Isaac 實際影像、視覺審查及 Static／Integrity／Native Support／Replay；下載數、場景實例數不當作可用資產數。
- Seed **706／707**，各三種密度：**Low 10–20、Medium 30–50、High 70–80** 個物件實例。
- 每個交付場景均實際執行 **30 秒、120 Hz、3,600 步 CPU PhysX 全房間測試**，包含原始房間剛體與關節；檢查最後兩秒穩定性、位移、支撐區域、依賴與有效姿態 Replay。
- 柔性形變暫緩。固定外形與剛體代理不代表布料操作、真實質量校準或任意未來 Seed 已驗證。

## 直接下載房間

[**下載 clean room 與六組範例場景**]({remote}/raw/refs/heads/main/{a.download}) · [封裝校驗資訊](docs/PACKAGE_STATUS.json)

完整解壓縮並保留 `assets/`，開啟 `clean_room.usda`，或選擇下列場景。一般版保留模擬後的生成物件姿態；`_dynamic.usda` 啟用已測試的剛體設定。僅拿走單一 USD 而省略依賴檔案，無法完整載入。

![公開版原生道具範例](docs/previews/public-high706.png)

**公開範例使用五個原房間道具紀錄，種類有限且含重複實例**；與擴充 Blendkit 研究池分開，不增加資產庫的獨立數量。原始來源、同意紀錄、封裝檔案對照均保留於下載包。

| Seed | 程度 | 實例數 | 全房間物理 | Preview | ZIP 內路徑 |
| --- | --- | ---: | --- | --- | --- |
{table}

## 重現：房間 → 生成 → 物理 → USD

`research/` 提供經權利範圍檢查的房間／原生道具輸入和獨立執行環境；既有 `toolkit/` 保留。

實測環境：Windows、Isaac Sim **6.0.0-rc.59**、其內建 Python、RTX5070Ti Laptop GPU。渲染使用 Direct3D12，剛體模擬使用 CPU PhysX；其他 SDK 版本尚未認證。請使用 Isaac 內建 Python，並依安裝位置調整執行檔路徑。

```powershell
{command}
```

指令會生成兩個 Seed 的三種程度，執行有上限的物理回饋重採樣，輸出 settled／dynamic USD，檢查來源 SHA、物理、Replay 與依賴，並拍攝實際影像。新結果位於 `research/_asset_library_blendkit/runs/`；每次使用新的 tag。公開範例流程不需 Blendkit 登入、訂閱或下載 API。

## 資產及授權範圍

`docs/asset_sources.json` 保存 Blendkit 原始 ID、作者、來源網址、版本、來源 SHA 與不同權利門檻。免費取得、本機技術通過，不等於可散布可抽取 USD。Blendkit 的 GENERATION_READY／公開 Starter 仍為 {status['generation_ready']}／{status['public_starter']}，與另獲同意的原房間範例分開計算。

專案維護者於2026/11/18確認 Hotel705 房間及原生道具的作者／實驗室散布同意；未對第三方內容宣告概括授權。詳見 [權利範圍](RIGHTS.md)、[授權狀態](LICENSE_STATUS.md)、[交付範圍](docs/DELIVERY_SCOPE.md)。保留原房間出處；不含 Blendkit 原始模型／貼圖、Add-on、使用者設定、帳密、SDK 或論文 PDF。

結果代表指定案例的研究驗證，不是機器人安全或任意場景的物理認證。
'''
    english+='\n## Progress presentation\n\n[19 November research report (editable PowerPoint)](reports/2026-11-19/hotel_room_weekly_20261119_editable.pptx)\n'
    chinese+='\n## 研究進度簡報\n\n[11/19 研究報告（可編輯 PowerPoint）](reports/2026-11-19/hotel_room_weekly_20261119_editable.pptx)\n'
    archive=checkout/'docs/archive/README_before_20261119.md';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():archive.write_bytes((checkout/'README.md').read_bytes())
    (checkout/'README.md').write_text(english,encoding='utf-8');(checkout/'README.zh-TW.md').write_text(chinese,encoding='utf-8')
    write(ROOT/'reports/bilingual_readme_preparation.json',dict(outcome='WRITTEN_FROM_VERIFIED_RESULTS',local_run=str(a.local_run),public_run=str(a.public_run),
        english_sha256=sha(checkout/'README.md'),chinese_sha256=sha(checkout/'README.zh-TW.md'),download_sha256=sha(download)))
    print('BILINGUAL_READMES_WRITTEN',stats)


if __name__=='__main__':main()
