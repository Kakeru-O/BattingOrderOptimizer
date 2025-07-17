import streamlit as st
import pandas as pd
from app.services.simulation import simulate_game, estimate_best_batting_order


TEAM_ABBREVIATIONS = {
    "ヤクルト": "s",
    "DeNA": "db",
    "阪神": "t",
    "巨人": "g",
    "広島": "c",
    "中日": "d",
    "オリックス": "b",
    "ソフトバンク": "h",
    "西武": "l",
    "楽天": "e",
    "ロッテ": "m",
    "日本ハム": "f",
}

@st.cache_data
def load_data(year, team):
    team_abbr = TEAM_ABBREVIATIONS[team]
    file_path = f"./data/processed/{year}_{team_abbr}.csv"
    try:
        # Player列をインデックスに設定しないように変更
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"{year}年の{team}のデータが見つかりません。")
        return pd.DataFrame()

def main():
    st.title("NPB Batting Order Optimizer")
    st.write("NPBの実際の選手成績データに基づき、最も得点効率の良い打順を探索するアプリケーションです。")

    st.sidebar.title("設定")
    year = st.sidebar.selectbox("年度を選択", list(range(2022, 2026)), index=2)

    teams = {
        "セントラル・リーグ": ["ヤクルト", "DeNA", "阪神", "巨人", "広島", "中日"],
        "パシフィック・リーグ": ["オリックス", "ソフトバンク", "西武", "楽天", "ロッテ", "日本ハム"]
    }
    league = st.sidebar.selectbox("リーグを選択", list(teams.keys()))
    team = st.sidebar.selectbox("チームを選択", teams[league])

    st.sidebar.title("最良打順推定")
    num_trials = st.sidebar.number_input("試行回数", min_value=10, max_value=10000, value=100)
    run_best_order_estimation = st.sidebar.button("最良打順を推定")

    df = load_data(year, team)

    if not df.empty:
        st.header(f"{year}年 {team} 選手一覧")
        st.dataframe(df)

        st.header("任意の打順でシミュレーション")
        player_names = df['Player'].tolist()
        batting_order_players = []
        # st.columnsを使用してレイアウトを調整
        cols = st.columns(3)
        for i in range(1, 10):
            with cols[(i-1)%3]:
                selected_player = st.selectbox(f"{i}番打者", player_names, index=i-1 if i-1 < len(player_names) else 0, key=f"player_{i}")
                batting_order_players.append(selected_player)
        
        if st.button("シミュレーション実行"):
            # 選手名から選手データを取得し、打順のDataFrameを作成
            batting_order_df = df[df['Player'].isin(batting_order_players)].set_index('Player')
            # 選択された順序に並び替え
            batting_order_df = batting_order_df.loc[batting_order_players].reset_index()

            result = simulate_game(batting_order_df, enable_inning_log=True)

            st.subheader("シミュレーション結果")
            st.metric("総得点", f"{result['total_runs']}点")

            # イニングごと詳細ログ
            with st.expander("イニングごとの詳細ログを見る"):
                inning_log_df = pd.DataFrame(result['inning_log']).T
                inning_log_df.columns = [f"{i}回" for i in range(1, 10)]
                # インデックスを選手名に設定
                inning_log_df.index = [f"{i+1}番: {name}" for i, name in enumerate(batting_order_players)]
                st.dataframe(inning_log_df)

            st.subheader("打者別成績")
            game_log_df = pd.DataFrame(result['game_log']).T
            # 選手名と打順を追加
            game_log_df['Player'] = batting_order_players
            game_log_df['Order'] = range(1, 10)
            game_log_df = game_log_df.set_index(['Order', 'Player'])
            st.dataframe(game_log_df)

        if run_best_order_estimation:
            st.header("最良打順推定結果")
            if len(batting_order_players) < 9:
                st.error("任意の打順で9人の選手を選択してください。")
            else:
                # ユーザーが選択した9人の選手を対象とする
                selected_players_for_estimation = df[df['Player'].isin(batting_order_players)].set_index('Player').loc[batting_order_players].reset_index()

                with st.spinner('シミュレーションを実行中...'):
                    progress_bar = st.progress(0)
                    estimation_result = estimate_best_batting_order(selected_players_for_estimation, num_trials, progress_bar)
                
                if estimation_result:
                    # 最良打順の表示
                    st.subheader("⚾ 最も得点効率の良い打順 (Best Order)")
                    st.metric("平均得点", f"{estimation_result['best_order']['avg_runs']:.2f}点")
                    st.metric("シーズン総得点", f"{estimation_result['best_order']['total_runs']:.0f}点")
                    best_order_df = estimation_result['best_order']['order_df']
                    
                    # 最良打順の選手別成績
                    st.subheader("最良打順 選手別成績")
                    best_stats_df = pd.DataFrame(estimation_result['best_order']['stats']).T
                    best_stats_df['Player'] = best_order_df['Player'].tolist()
                    best_stats_df['Order'] = range(1, 10)
                    best_stats_df = best_stats_df.set_index(['Order', 'Player'])
                    
                    # 各種指標の計算
                    best_stats_df['PA'] = best_stats_df[['1B', '2B', '3B', 'HR', 'BB+HBP', 'Out']].sum(axis=1)
                    best_stats_df['AB'] = best_stats_df[['1B', '2B', '3B', 'HR', 'Out']].sum(axis=1)
                    best_stats_df['H'] = best_stats_df[['1B', '2B', '3B', 'HR']].sum(axis=1)
                    best_stats_df['AVG'] = best_stats_df['H'] / best_stats_df['AB']
                    best_stats_df['OBP'] = (best_stats_df['H'] + best_stats_df['BB+HBP']) / best_stats_df['PA']
                    best_stats_df['TB'] = best_stats_df['1B'] + 2*best_stats_df['2B'] + 3*best_stats_df['3B'] + 4*best_stats_df['HR']
                    best_stats_df['SLG'] = best_stats_df['TB'] / best_stats_df['AB']
                    best_stats_df['OPS'] = best_stats_df['OBP'] + best_stats_df['SLG']

                    st.dataframe(best_stats_df[['PA', 'AB', 'H', '2B', '3B', 'HR', 'RBI', 'AVG', 'OBP', 'SLG', 'OPS']].fillna(0).round(3))

                    # 最悪打順の表示
                    st.subheader("👎 最も得点効率の悪い打順 (Worst Order)")
                    st.metric("平均得点", f"{estimation_result['worst_order']['avg_runs']:.2f}点")
                    st.metric("シーズン総得点", f"{estimation_result['worst_order']['total_runs']:.0f}点")
                    worst_order_df = estimation_result['worst_order']['order_df']
                    
                    # 最悪打順の選手別成績
                    st.subheader("最悪打順 選手別成績")
                    worst_stats_df = pd.DataFrame(estimation_result['worst_order']['stats']).T
                    worst_stats_df['Player'] = worst_order_df['Player'].tolist()
                    worst_stats_df['Order'] = range(1, 10)
                    worst_stats_df = worst_stats_df.set_index(['Order', 'Player'])

                    # 各種指標の計算
                    worst_stats_df['PA'] = worst_stats_df[['1B', '2B', '3B', 'HR', 'BB+HBP', 'Out']].sum(axis=1)
                    worst_stats_df['AB'] = worst_stats_df[['1B', '2B', '3B', 'HR', 'Out']].sum(axis=1)
                    worst_stats_df['H'] = worst_stats_df[['1B', '2B', '3B', 'HR']].sum(axis=1)
                    worst_stats_df['AVG'] = worst_stats_df['H'] / worst_stats_df['AB']
                    worst_stats_df['OBP'] = (worst_stats_df['H'] + worst_stats_df['BB+HBP']) / worst_stats_df['PA']
                    worst_stats_df['TB'] = worst_stats_df['1B'] + 2*worst_stats_df['2B'] + 3*worst_stats_df['3B'] + 4*worst_stats_df['HR']
                    worst_stats_df['SLG'] = worst_stats_df['TB'] / worst_stats_df['AB']
                    worst_stats_df['OPS'] = worst_stats_df['OBP'] + worst_stats_df['SLG']

                    st.dataframe(worst_stats_df[['PA', 'AB', 'H', '2B', '3B', 'HR', 'RBI', 'AVG', 'OBP', 'SLG', 'OPS']].fillna(0).round(3))
                else:
                    st.error("シミュレーション結果を取得できませんでした。")

if __name__ == "__main__":
    main()