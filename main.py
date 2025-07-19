import streamlit as st
import pandas as pd
import random
# app/services/simulation.py は同じ階層にあると仮定
from app.services.simulation import simulate_game, estimate_best_batting_order

# 定数
TEAM_ABBREVIATIONS = {
    "ヤクルト": "s", "DeNA": "db", "阪神": "t", "巨人": "g", "広島": "c", "中日": "d",
    "オリックス": "b", "ソフトバンク": "h", "西武": "l", "楽天": "e", "ロッテ": "m", "日本ハム": "f",
}

# --- データ読み込み関数 ---
@st.cache_data
def load_data(year, team):
    """指定された年とチームの選手成績データを読み込む"""
    team_abbr = TEAM_ABBREVIATIONS[team]
    file_path = f"./data/processed/{year}_{team_abbr}.csv"
    file_path2 = f"./data/raw/{year}_{team_abbr}.csv"
    
    try:
        df1 = pd.read_csv(file_path)
        df2 = pd.read_csv(file_path2)
        return df1,df2
    except FileNotFoundError:
        st.error(f"エラー: {year}年の{team}のデータが見つかりません。")
        st.stop() # データが見つからない場合は処理を停止

@st.cache_data
def load_default_lineups(year):
    """指定された年のデフォルトスタメンデータを読み込む"""
    file_path = f"./data/processed/default_lineups_{year}.csv"
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.warning(f"警告: {year}年のデフォルトスタメンデータが見つかりません。")
        return pd.DataFrame()

# --- ヘルパー関数 ---
def get_initial_players(df, default_lineups_df, year, team):
    """multiselectの初期選択選手リストを取得する"""
    player_names = df['Player'].tolist()
    team_abbr_upper = TEAM_ABBREVIATIONS[team].upper()
    
    team_default_df = default_lineups_df[
        (default_lineups_df['Year'] == int(year)) & 
        (default_lineups_df['Team_Abbr'] == team_abbr_upper)
    ]

    if not team_default_df.empty:
        position_order = ['捕', '一', '二', '三', '遊', '左', '中', '右', '指']
        team_default_df['Position_Order'] = pd.Categorical(
            team_default_df['Position'], categories=position_order, ordered=True
        )
        initial_players = team_default_df.sort_values('Position_Order')['Player'].tolist()
    else:
        initial_players = player_names[:9]
        
    if len(initial_players) < 9:
        remaining_players = [p for p in player_names if p not in initial_players]
        random.shuffle(remaining_players)
        initial_players.extend(remaining_players[:9 - len(initial_players)])
        
    return initial_players[:9]

def calculate_player_stats(stats_df):
    """シミュレーション結果から各種成績を計算する"""
    required_cols = ['1B', '2B', '3B', 'HR', 'BB+HBP', 'SO', 'Ground_Out', 'Fly_Out', 'Sacrifice_Attempts', 'RBI', 'Sacrifice_Success']
    for col in required_cols:
        if col not in stats_df.columns:
            stats_df[col] = 0

    stats_df['Out'] = stats_df['SO'] + stats_df['Ground_Out'] + stats_df['Fly_Out']
    stats_df['PA'] = stats_df[['1B', '2B', '3B', 'HR', 'BB+HBP', 'SO', 'Ground_Out', 'Fly_Out', 'Sacrifice_Attempts']].sum(axis=1)
    stats_df['AB'] = stats_df[['1B', '2B', '3B', 'HR', 'SO', 'Ground_Out', 'Fly_Out']].sum(axis=1)
    stats_df['H'] = stats_df[['1B', '2B', '3B', 'HR']].sum(axis=1)
    stats_df['TB'] = stats_df['1B'] + 2*stats_df['2B'] + 3*stats_df['3B'] + 4*stats_df['HR']
    
    stats_df['AVG'] = (stats_df['H'] / stats_df['AB']).where(stats_df['AB'] > 0, 0)
    stats_df['OBP'] = ((stats_df['H'] + stats_df['BB+HBP']) / stats_df['PA']).where(stats_df['PA'] > 0, 0)
    stats_df['SLG'] = (stats_df['TB'] / stats_df['AB']).where(stats_df['AB'] > 0, 0)
    
    stats_df['OPS'] = stats_df['OBP'] + stats_df['SLG']
    return stats_df

# --- メインアプリケーション ---
def main():
    st.set_page_config(page_title="NPB打順シミュレーター", layout="wide")
    st.title("⚾ NPB打順シミュレーター")
    st.write("NPBの選手データに基づき、打順による得点効率をシミュレーションします。任意の9人を選んで1試合のシミュレーションを行ったり、そのメンバーでの最適打順を推定したりできます。")

    # --- サイドバー設定 ---
    st.sidebar.title("📊 シミュレーション設定")
    year = st.sidebar.selectbox("年度を選択", list(range(2022, 2026)), index=2)
    
    teams = {
        "セントラル・リーグ": ["ヤクルト", "DeNA", "阪神", "巨人", "広島", "中日"],
        "パシフィック・リーグ": ["オリックス", "ソフトバンク", "西武", "楽天", "ロッテ", "日本ハム"]
    }
    league = st.sidebar.selectbox("リーグを選択", list(teams.keys()))
    team = st.sidebar.selectbox("チームを選択", teams[league])

    # チーム/年度が変更された場合、選択中の選手をリセットして再実行
    if 'last_config' not in st.session_state or st.session_state.last_config != (year, team):
        st.session_state.last_config = (year, team)
        if 'multiselect_players' in st.session_state:
             del st.session_state['multiselect_players']
        st.rerun()

    # --- データ読み込み ---
    df,df2 = load_data(year, team)
    default_lineups_df = load_default_lineups(year)

    if df.empty:
        st.info("データを読み込めませんでした。サイドバーで有効な年度とチームを選択してください。")
        return

    # --- 選手データ表示 ---
    with st.expander(f"📊 {year}年 {team} の選手一覧を表示"):
        st.dataframe(df2)

    st.markdown("---")
    st.header("📝 打順を編成")
    st.write("打順に含める9人の選手を選択してください。リストの並び順がそのまま1番から9番の打順になります。")

    # --- 選手選択 ---
    player_names = df['Player'].tolist()
    if 'multiselect_players' not in st.session_state:
        initial_players = get_initial_players(df, default_lineups_df, year, team)
    else:
        initial_players = st.session_state.multiselect_players

    selected_players = st.multiselect(
        "打順 (1番〜9番)",
        options=player_names,
        default=initial_players,
        max_selections=9,
        key="multiselect_players"
    )

    if len(selected_players) != 9:
        st.warning("⚠️ 9人の選手を選択してください。")
        return

    # 選択された選手データを準備
    try:
        selected_players_df = df[df['Player'].isin(selected_players)].set_index('Player').loc[selected_players].reset_index()
    except KeyError:
        st.error("選手データの読み込みに失敗しました。ページを再読み込みするか、選手を再選択してください。")
        return

    # --- シミュレーション実行 ---
    st.markdown("---")

    st.subheader("🎲 1試合シミュレーション")
    if st.button("この打順で実行", key="run_single_sim", use_container_width=True, type="primary"):
        result = simulate_game(selected_players_df, enable_inning_log=True)
        st.metric("総得点", f"{result['total_runs']}点")
        
        st.write("詳細なプレイログ")
        inning_log_df = pd.DataFrame(result['inning_log']).T
        inning_log_df.columns = [f"{i}回" for i in range(1, 10)]
        inning_log_df.index = [f"{i+1}番: {name}" for i, name in enumerate(selected_players)]
        st.dataframe(inning_log_df)

        st.write("打者別成績")
        game_log_df = pd.DataFrame(result['game_log']).T
        game_log_df = calculate_player_stats(game_log_df)
        game_log_df['Player'] = selected_players
        game_log_df['Order'] = range(1, 10)
        game_log_df = game_log_df.set_index(['Order', 'Player'])
        st.dataframe(game_log_df[['PA', 'AB', 'H', '2B','3B','HR','BB+HBP','SO','Out','Sacrifice_Success', 'RBI', 'AVG', 'OBP', 'SLG', 'OPS']].fillna(0).round(3),use_container_width=True)

    st.subheader("🏆 最良打順の推定")
    num_trials = st.number_input("試行回数", min_value=10, max_value=10000, value=100, step=10, help="試行回数が多いほど精度が向上しますが、計算に時間がかかります。")
    
    if st.button("このメンバーで推定", key="run_best_order_sim", use_container_width=True):
        with st.spinner('シミュレーションを実行中...'):
            progress_bar = st.progress(0, text="処理開始...")
            estimation_result = estimate_best_batting_order(selected_players_df, num_trials, progress_bar)
        
        if estimation_result:
            st.write("##### ✨ 最も得点効率の良い打順 (Best)")
            st.metric("平均得点 (Best)", f"{estimation_result['best_order']['avg_runs']:.2f}点")
            best_order_players = estimation_result['best_order']['order_df']['Player'].tolist()
            best_df = pd.DataFrame({'Order': range(1, 10), 'Player': best_order_players})
            #st.dataframe(best_df, use_container_width=True, hide_index=True)
            best_stats_df = pd.DataFrame(estimation_result['best_order']['stats']).T
            best_stats_df = calculate_player_stats(best_stats_df)
            #st.dataframe(best_stats_df)#[[]].fillna(0).round(3))
            best_df = pd.concat([best_df,best_stats_df],axis=1)
            st.dataframe(best_df[["Order","Player",'PA', 'AB', 'H', '2B','3B','HR','BB+HBP','SO','Out','Sacrifice_Success', 'RBI', 'AVG', 'OBP', 'SLG', 'OPS']].fillna(0).round(3),use_container_width=True, hide_index=True)

            st.write("##### 💔 最も得点効率の悪い打順 (Worst)")
            st.metric("平均得点 (Worst)", f"{estimation_result['worst_order']['avg_runs']:.2f}点")
            worst_order_players = estimation_result['worst_order']['order_df']['Player'].tolist()
            worst_df = pd.DataFrame({'Order': range(1, 10), 'Player': worst_order_players})
            #st.dataframe(worst_df, use_container_width=True, hide_index=True)
            worst_stats_df = pd.DataFrame(estimation_result['worst_order']['stats']).T
            worst_stats_df = calculate_player_stats(worst_stats_df)
            worst_df = pd.concat([worst_df,worst_stats_df],axis=1)
            st.dataframe(worst_df[["Order","Player",'PA', 'AB', 'H', '2B','3B','HR','BB+HBP','SO','Out','Sacrifice_Success', 'RBI', 'AVG', 'OBP', 'SLG', 'OPS']].fillna(0).round(3),use_container_width=True, hide_index=True)

            

        else:
            st.error("シミュレーション結果の取得に失敗しました。")


if __name__ == "__main__":
    main()