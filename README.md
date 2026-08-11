# entrance_monitor
入退室の監視をしてくれるRaspberryPiツール（NFCのみ対応）

## 初期設定

1. `config.py.sample` を `config.py` にコピーする
2. `config.py` を環境に合わせて編集する（WiFi AP、RFID カード登録など）
3. 本体に `/storage/auth.cfg` を置く（`auth.cfg.sample` をコピーして編集）

`config.py` は git 管理外です。設定項目の追加・デフォルト値の変更は `config.py.sample` を更新してください。

### ログイン（TOP）

- URL: `http://<IP>/`（ログイン画面）
- 認証ファイル: `/storage/auth.cfg`（1行 `user:password`。`#` 行・空行は無視）
- 例: `admin:change-me`
- 成功後は `/admin?key=<SECRET_KEY>` へ誘導（既存の token 機構を流用）
- ログ一覧: `/logs`
- **`ENABLE_TOKEN_CHECK = True` を推奨**（False だと `/admin` 直打ちでログインを回避できる）

## プログラムの無線更新

本体 AP に接続し、ブラウザで管理メニューを開く。

1. WiFi: `config.py` の `SSID` / `PASSWORD` で AP に接続
2. `http://192.168.4.1/` でログイン
3. **保守** → **新規**（`/admin/maintain/upload`）から `.py` / `.cfg` / `.txt` を送信
4. 必要なら「reboot」にチェック（新規アップロードは既定 ON）

旧 URL `/admin/upload` は新規アップロードへ誘導します。

`ENABLE_TOKEN_CHECK = True` のときは URL / フォームに `key` が付きます。

転送上限は `HTTP_MAX_REQ_SIZE`（既定 **20480 バイト**）で、**HTTP ヘッダ＋multipart 全体**が対象です。  
ファイル本体だけが入るわけではなく、ヘッダ分を引いたサイズ以下にしてください。超過すると受信せず 400/413 を返します。  
Pico W で `65536` など大きすぎる値にすると、アップロード中に **OutOfMemory** になりやすいです。

## 保守（ファイル・ログ）

管理メニューの **保守**（`/admin/maintain`）から、本体フラッシュ上のファイルを操作できます。

- ディレクトリ一覧（`/`・`/lib`・`/fonts`・`/storage` など）
- **新規アップロード**（保存名・保存先・拡張子制限あり）
- テキスト編集（`.py` / `.cfg` / `.txt` / `.csv`、約 8KB 以下）
- 既存パスへの上書き（`put`、拡張子制限なし）
- ファイル削除（確認ページあり）
- **ログ削除**（保守ページ内リンク → `/admin/maintain/logs`）
- **ログ一覧**は `/logs`

`main.py` / `boot.py` / `config.py` を消すと起動できなくなることがあるので注意してください。

Pico W は RAM が少ないため、重いページでメモリ不足になると HTTP だけ止まることがあります（ping は通る）。その場合は電源再投入し、最新の `http_server.py` / `http_util.py` / `http_admin.py` / `http_time.py` / `http_maintain.py` を入れてください（無線アップロードはファイルごとに分割）。
