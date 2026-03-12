import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import html
import streamlit.components.v1 as components
import datetime
import re
import math

# --- 設定 ---
PAGE_TITLE = "YouTube Shorts 分析 ダッシュボード"
SPREADSHEET_NAME = 'YouTubeデータ収集DB_Shorts' # ショート用のシート名に合わせる

# --- 🔐 セキュリティ: パスワード認証 ---
TEAM_PASSWORD = "shortmore"

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct:
        return True
    st.markdown("### 🔒 ログインが必要です")
    pwd = st.text_input("パスワードを入力してください", type="password")
    if pwd == TEAM_PASSWORD:
        st.session_state.password_correct = True
        st.rerun()
    elif pwd:
        st.error("パスワードが違います")
    return False

if not check_password():
    st.stop()

# --- ☁️ クラウド対応: 認証情報の読み込み ---
@st.cache_resource
def get_credentials():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    
    # Secrets (TOML/JSON) 対応
    if "gcp_service_account" in st.secrets:
        try:
            val = st.secrets["gcp_service_account"]
            if isinstance(val, str):
                creds_json = json.loads(val)
                return Credentials.from_service_account_info(creds_json, scopes=scope)
            else:
                return Credentials.from_service_account_info(dict(val), scopes=scope)
        except Exception as e:
            st.error(f"Secrets読み込みエラー: {e}")
            return None

    # ローカルファイル対応
    if os.path.exists('credentials.json'):
        return Credentials.from_service_account_file('credentials.json', scopes=scope)
    
    return None

# --- カラム定義 ---
COLS_FORMAT = ['企画フォーマット分類', 'Format (修正後)', 'Format']
COLS_TAGS = ['成功パターン分類（タグ）', 'Success Tags (修正後)', 'Tags']
COLS_HYPOTHESIS = ['成功要因仮説（パッケージング）', 'Success Hypothesis (修正後)', 'Success Hypothesis']
COLS_IDEAS = ['転用アイデア・示唆', 'Transferable Ideas (修正後)', 'Transferable Ideas']
COLS_SCORE = ['Scalability Score (修正後)', 'Scalability Score']

COL_VIDEO_ID = 'Video ID'
COL_TITLE = 'Title'
COL_CHANNEL = 'Channel Name'
COL_PUBLISHED = 'Published At'
COL_PERF = 'Relative Performance (%)'
COL_THUMBNAIL = 'Thumbnail URL'
COL_VIEW = 'View Count'
COL_URL = 'URL'

def generate_html_card(row, col_map):
    def val(key, default='-'): 
        v = row.get(key)
        return html.escape(str(v)) if pd.notna(v) and v != "" else default
    try: score = int(float(row.get(col_map['score'], 0)))
    except: score = 0
    stars = "★" * score + "☆" * (5 - score)
    tags = str(row.get(col_map['tags'], '')).split(',')
    tags_html = "".join([f"<span class='tag'>{html.escape(t.strip())}</span>" for t in tags if t.strip()])
    
    style = """
    <style>
        .report-card { font-family: "Helvetica Neue", Arial, sans-serif; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; display: flex; flex-wrap: wrap; gap: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .col-left { flex: 1; min-width: 200px; max-width: 250px; } /* 少し細めにする */
        .col-right { flex: 2; min-width: 300px; } /* ←この行はそのまま残します */
        .thumb { width: 100%; aspect-ratio: 9/16; object-fit: cover; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; } /* 縦長対応 */
        .metric-box { background: #f8f9fa; padding: 15px; border-radius: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .metric-item { display: flex; flex-direction: column; }
        .metric-label { font-size: 0.8em; color: #666; font-weight: bold; }
        .metric-value { font-size: 1.1em; font-weight: bold; color: #333; }
        .highlight { color: #d9534f; }
        .section { margin-bottom: 15px; }
        .sec-title { font-weight: bold; color: #333; border-left: 4px solid #0056b3; padding-left: 8px; margin-bottom: 5px; background: #f0f8ff; padding-top:2px; padding-bottom:2px;}
        .sec-body { font-size: 0.95em; line-height: 1.6; color: #444; white-space: pre-wrap; background: #fafafa; padding: 8px; border-radius: 4px; border: 1px solid #eee; }
        .tag { display: inline-block; background: #e9ecef; padding: 3px 10px; margin: 2px; border-radius: 12px; font-size: 0.8em; color: #555; }
        .report-title { font-size: 1.4em; font-weight: bold; color: #0056b3; text-decoration: none; display: block; margin-bottom: 5px; line-height: 1.3; }
        .report-meta { font-size: 0.9em; color: #777; margin-bottom: 15px; }
    </style>
    """
    html_content = f"""
    {style}
    <div class="report-card">
        <div class="col-left">
            <a href="{row.get(COL_URL)}" target="_blank"><img src="{row.get(COL_THUMBNAIL)}" class="thumb"></a>
            <div class="metric-box">
                <div class="metric-item"><span class="metric-label">Relative Performance</span><span class="metric-value highlight">{row.get(COL_PERF)}%</span></div>
                <div class="metric-item"><span class="metric-label">Scalability</span><span class="metric-value" style="color:#f1c40f">{stars}</span></div>
                <div class="metric-item"><span class="metric-label">Views</span><span class="metric-value">{int(row.get(COL_VIEW, 0)):,}</span></div>
                <div class="metric-item"><span class="metric-label">Published</span><span class="metric-value">{str(row.get(COL_PUBLISHED))[:10]}</span></div>
            </div>
        </div>
        <div class="col-right">
            <a href="{row.get(COL_URL)}" target="_blank" class="report-title">{val(COL_TITLE)}</a>
            <div class="report-meta">by {val(COL_CHANNEL)}</div>
            <div class="section"><div class="sec-title">企画フォーマット</div><div class="sec-body">{val(col_map['format'])}</div></div>
            <div class="section"><div class="sec-title">成功パターン (Tags)</div><div>{tags_html}</div></div>
            <div class="section"><div class="sec-title">成功要因仮説 (Hypothesis)</div><div class="sec-body">{val(col_map['hypo'])}</div></div>
            <div class="section"><div class="sec-title">転用アイデア (Ideas)</div><div class="sec-body">{val(col_map['idea'])}</div></div>
        </div>
    </div>
    """
    return html_content

@st.cache_data(ttl=600)
def load_data():
    creds = get_credentials()
    if not creds: return pd.DataFrame()
    try:
        client = gspread.authorize(creds)
        worksheet = client.open(SPREADSHEET_NAME).get_worksheet(0)
        df = pd.DataFrame(worksheet.get_all_records())
        if not df.empty:
            for col in [COL_PERF, COL_VIEW]:
                if col in df.columns:
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '').str.replace('%', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if COL_PUBLISHED in df.columns:
                df[COL_PUBLISHED] = pd.to_datetime(df[COL_PUBLISHED], errors='coerce')
        return df
    except Exception as e:
        return pd.DataFrame()

def get_col_name(df, candidates):
    for col in candidates:
        if col in df.columns: return col
    return None

# ★【軽量版】類似動画検索（scikit-learn不使用でメモリ節約）
def find_similar_videos_lightweight(df, target_id, col_map):
    if df.empty: return pd.DataFrame()
    
    # ターゲット動画の情報を取得
    target_row = df[df[COL_VIDEO_ID] == target_id]
    if target_row.empty: return pd.DataFrame()
    target_row = target_row.iloc[0]
    
    # テキストをセット（単語の集合）に変換するヘルパー関数
    def get_tokens(text):
        if pd.isna(text): return set()
        # 簡易的な分かち書き（空白や句読点で区切る）
        text = str(text).lower()
        return set(re.split(r'\s+|、|。|,', text))

    # ターゲットの特徴語
    tgt_text = str(target_row.get(col_map['format'], '')) + " " + \
               str(target_row.get(col_map['tags'], '')) + " " + \
               str(target_row.get(col_map['hypo'], ''))
    tgt_tokens = get_tokens(tgt_text)
    
    if not tgt_tokens: return pd.DataFrame()

    scores = []
    for idx, row in df.iterrows():
        if row[COL_VIDEO_ID] == target_id: continue
        
        # 比較対象の特徴語
        row_text = str(row.get(col_map['format'], '')) + " " + \
                   str(row.get(col_map['tags'], '')) + " " + \
                   str(row.get(col_map['hypo'], ''))
        row_tokens = get_tokens(row_text)
        
        if not row_tokens:
            scores.append((idx, 0))
            continue
            
        # Jaccard係数（共通する単語の割合）を計算
        intersection = len(tgt_tokens & row_tokens)
        union = len(tgt_tokens | row_tokens)
        score = intersection / union if union > 0 else 0
        
        if score > 0:
            scores.append((idx, score))
    
    # スコア順にソートしてトップ5を返す
    scores.sort(key=lambda x: x[1], reverse=True)
    top_5 = scores[:5]
    
    res = df.iloc[[i[0] for i in top_5]].copy()
    res['Score'] = [i[1] for i in top_5]
    return res

def main():
    st.set_page_config(page_title=PAGE_TITLE, layout="wide", page_icon="📊")
    
    df = load_data()
    if df.empty:
        st.stop()

    col_map = {
        'format': get_col_name(df, COLS_FORMAT),
        'tags': get_col_name(df, COLS_TAGS),
        'hypo': get_col_name(df, COLS_HYPOTHESIS),
        'idea': get_col_name(df, COLS_IDEAS),
        'score': get_col_name(df, COLS_SCORE)
    }

    # --- サイドバー ---
    st.sidebar.title("🔍 検索 & フィルタ")
    search_q = st.sidebar.text_input("キーワード検索", placeholder="タイトル, タグ, チャンネル...")
    
    import datetime
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=90)
    
    st.sidebar.subheader("投稿期間")
    use_date = st.sidebar.checkbox("期間で絞り込む", value=False)
    date_range = []
    if use_date:
        date_range = st.sidebar.date_input("範囲選択", (default_start, today))
    
    channels = sorted([str(x) for x in df[COL_CHANNEL].unique() if x])
    sel_ch = st.sidebar.multiselect("チャンネル", channels)
    
    if col_map['format']:
        fmts = set()
        for x in df[col_map['format']].astype(str):
            for f in x.replace('、', ',').split(','):
                if f.strip(): fmts.add(f.strip())
        sel_fmt = st.sidebar.multiselect("企画フォーマット", sorted(list(fmts)))
    else: sel_fmt = []
    
    min_perf = st.sidebar.slider("最低 Perf (%) [ヒット判定用]", 0, 300, 100, step=10, help="この値以上のPerfを持つ動画を「ヒット」としてカウントします")

    # --- フィルタリング ---
    base_mask = pd.Series(True, index=df.index)
    if search_q:
        q = search_q.lower()
        search_mask = df[COL_TITLE].str.lower().str.contains(q, na=False) | \
                      df[COL_CHANNEL].str.lower().str.contains(q, na=False)
        if col_map['tags']: search_mask |= df[col_map['tags']].str.lower().str.contains(q, na=False)
        base_mask &= search_mask

    if use_date and len(date_range) == 2:
        s, e = date_range
        base_mask &= (df[COL_PUBLISHED].dt.date >= s) & (df[COL_PUBLISHED].dt.date <= e)

    if sel_ch: base_mask &= df[COL_CHANNEL].isin(sel_ch)
    if sel_fmt: base_mask &= df[col_map['format']].astype(str).apply(lambda x: any(f in x for f in sel_fmt))
    
    # ★ 実績サマリ用（母集団）
    base_filtered = df[base_mask].copy()

    # ★ リスト表示用（Perfフィルタ適用）
    display_filtered = base_filtered[base_filtered[COL_PERF] >= min_perf].copy()

    # --- メイン画面 ---
    st.title(PAGE_TITLE)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("List Videos", f"{len(display_filtered)}", help="表示中の動画数")
    c2.metric("Avg Perf (List)", f"{display_filtered[COL_PERF].mean():.1f}%" if not display_filtered.empty else "-", help="表示中の動画の平均Perf")
    c3.metric("Max Views", f"{int(display_filtered[COL_VIEW].max()):,}" if not display_filtered.empty else "-")
    c4.metric("期間", f"{date_range[0]}~{date_range[1]}" if use_date and len(date_range)==2 else "全期間")

    tab_list, tab_sim = st.tabs(["📋 リスト・詳細レポート", "🧠 類似企画検索"])

# --------------------------------------------------------------------------
    # Tab 1: カード型リスト表示（ページネーション付き・Shorts特化レイアウト）
    # --------------------------------------------------------------------------
    with tab_list:
        sc1, sc2 = st.columns([2, 1])
        s_key = sc1.selectbox("ソート基準", ["投稿日時 (新しい順)", "企画の強さ (Rel. Perf順)", "再生回数 (多い順)"])
        s_asc = sc2.radio("順序", ["降順", "昇順"], horizontal=True) == "昇順"
        
        if "企画" in s_key: sort_col = COL_PERF
        elif "再生" in s_key: sort_col = COL_VIEW
        else: sort_col = COL_PUBLISHED
        
        sorted_df = display_filtered.sort_values(by=sort_col, ascending=s_asc)
        
        # --- ページネーション設定 ---
        ITEMS_PER_PAGE = 50
        total_items = len(sorted_df)
        
        if total_items > 0:
            total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
            st.divider()
            
            # ページネーションコントロール（上部）
            p_col1, p_col2 = st.columns([3, 1])
            with p_col2:
                current_page = st.number_input("ページ選択", min_value=1, max_value=total_pages, value=1, step=1)
            
            # データスライス
            start_idx = (current_page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            page_df = sorted_df.iloc[start_idx:end_idx]
            
            with p_col1:
                display_start = start_idx + 1
                display_end = min(end_idx, total_items)
                st.info(f"全 {total_items} 件中、{display_start} ～ {display_end} 件目を表示しています（Page {current_page}/{total_pages}）")
        else:
            page_df = pd.DataFrame()
            st.warning("表示するデータがありません。")

        # --- カード表示ループ ---
        for _, row in page_df.iterrows():
            with st.container(border=True):
                # ★Shorts用調整: 縦長サムネが大きくなりすぎないよう [1, 3] または [1, 4] の比率にする
                col_img, col_info = st.columns([1, 3]) 
                
                with col_img:
                    # サムネイル表示
                    if row.get(COL_THUMBNAIL):
                        st.image(row[COL_THUMBNAIL], use_container_width=True)
                    else:
                        st.text("No Image")

                with col_info:
                    # タイトル（リンク付き）
                    st.markdown(f"#### [{row[COL_TITLE]}]({row[COL_URL]})")
                    
                    # メタ情報
                    st.caption(f"📺 **{row[COL_CHANNEL]}** | 📅 {str(row[COL_PUBLISHED])[:10]}")
                    
                    # 数値指標
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Rel. Perf", f"{int(row[COL_PERF])}%")
                    m2.metric("Views", f"{int(row[COL_VIEW]):,}")
                    
                    # スコア
                    try: score = int(float(row.get(col_map['score'], 0)))
                    except: score = 0
                    stars = "★" * score + "☆" * (5 - score)
                    m3.metric("Scalability", stars)
                    
                    # 企画フォーマット
                    fmt = row.get(col_map['format'], '-')
                    if fmt:
                        st.markdown(f"**Format:** `{fmt}`")
                        
                    # タグ
                    tags = str(row.get(col_map['tags'], '')).split(',')
                    tags = [t.strip() for t in tags if t.strip()]
                    if tags:
                        tag_str = " ".join([f"`{t}`" for t in tags])
                        st.markdown(f"**Tags:** {tag_str}")

                # 分析詳細（アコーディオン）
                with st.expander("💡 分析・仮説を見る"):
                    st.markdown("#### 成功要因仮説")
                    st.info(row.get(col_map['hypo'], '記述なし'))
                    
                    st.markdown("#### 転用アイデア")
                    st.success(row.get(col_map['idea'], '記述なし'))

        if total_items > ITEMS_PER_PAGE:
            st.caption(f"現在のページ: {current_page} / {total_pages}")

        # -------------------------------------------------------------------
        # 【実績サマリ】
        # -------------------------------------------------------------------
        if not base_filtered.empty:
            st.divider()
            summary_label = f"「{search_q}」の分析サマリ" if search_q else "フィルタ条件全体のサマリ"
            st.subheader(f"📊 {summary_label}")
            
            total_count = len(base_filtered)
            avg_base_perf = base_filtered[COL_PERF].mean()
            hit_count = len(display_filtered)
            hit_rate = (hit_count / total_count * 100) if total_count > 0 else 0
            
            k1, k2, k3 = st.columns(3)
            k1.metric("対象動画数 (母数)", f"{total_count} 本", help=f"Perfフィルタ適用前の全動画数")
            k2.metric("平均 Performance", f"{avg_base_perf:.1f}%")
            k3.metric(
                label=f"ヒット率 (Perf≧{min_perf}%)",
                value=f"{hit_rate:.1f}%",
                delta=f"{hit_count}本 / {total_count}本",
                delta_color="off"
            )
        # 詳細レポート表示
        if event is not None and hasattr(event, "selection") and event.selection.rows:
            sel_idx = event.selection.rows[0]
            target_row = display_df.iloc[sel_idx]
            target_title = target_row.name
            st.divider()
            st.subheader(f"📑 分析レポート: {target_title}")
            row_dict = target_row.to_dict()
            row_dict[COL_TITLE] = target_title
            
            if col_map['hypo'] and pd.notna(row_dict.get(col_map['hypo'])) and len(str(row_dict.get(col_map['hypo']))) > 5:
                html_rep = generate_html_card(row_dict, col_map)
                components.html(html_rep, height=500, scrolling=True)
                file_name = f"Report_{row_dict.get(COL_VIDEO_ID, 'video')}.html"
                st.download_button("📥 HTMLレポートをダウンロード", html_rep, file_name, "text/html")
            else:
                st.warning("詳細分析データがありません。")

    with tab_sim:
        opts_df = display_filtered[display_filtered[col_map['hypo']].astype(str).str.len() > 5]
        if opts_df.empty: opts_df = df[df[col_map['hypo']].astype(str).str.len() > 5]
        
        opts = opts_df[COL_VIDEO_ID].tolist()
        lbls = [f"[{r[COL_CHANNEL]}] {r[COL_TITLE]}" for _, r in opts_df.iterrows()]
        
        if opts:
            vid = st.selectbox("分析元の動画", opts, format_func=lambda x: lbls[opts.index(x)] if x in opts else x)
            if vid:
                tgt_rows = df[df[COL_VIDEO_ID]==vid]
                if not tgt_rows.empty:
                    tgt = tgt_rows.iloc[0]
                    st.markdown(f"**元動画の仮説:** {tgt.get(col_map['hypo'])}")
                    st.divider()
                    st.write("#### ▼ 類似動画")
                    # 軽量版ロジックを使用
                    sims = find_similar_videos_lightweight(df, vid, col_map)
                    
                    if sims.empty:
                        st.info("類似する動画は見つかりませんでした。")
                    else:
                        for _, r in sims.iterrows():
                            with st.expander(f"類似度 {r['Score']:.2f}: {r[COL_TITLE]}"):
                                c1, c2 = st.columns([1, 3])
                                c1.image(r[COL_THUMBNAIL])
                                c2.caption(f"{r[COL_CHANNEL]} | Perf: {r[COL_PERF]}%")
                                c2.write(f"仮説: {r.get(col_map['hypo'])}")

if __name__ == "__main__":
    main()


