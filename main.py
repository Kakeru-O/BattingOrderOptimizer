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
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"エラー: {year}年の{team}のデータが見つかりません。サイドバーで別の年度・チームを選択してください。")
        st.stop() # データが見つからない場合はここで処理を停止
        return pd.DataFrame() # unreachable

def calculate_player_stats(stats_df):
    # 新しいOutの定義
    stats_df['Out'] = stats_df['SO'] + stats_df['Ground_Out'] + stats_df['Fly_Out']
    # PAの計算にSacrifice_Attemptsを含める
    stats_df['PA'] = stats_df[['1B', '2B', '3B', 'HR', 'BB+HBP', 'SO', 'Ground_Out', 'Fly_Out', 'Sacrifice_Attempts']].sum(axis=1)
    stats_df['AB'] = stats_df[['1B', '2B', '3B', 'HR', 'SO', 'Ground_Out', 'Fly_Out']].sum(axis=1) # ABは犠打を含まない
    stats_df['H'] = stats_df[['1B', '2B', '3B', 'HR']].sum(axis=1)
    stats_df['AVG'] = stats_df['H'] / stats_df['AB']
    stats_df['OBP'] = (stats_df['H'] + stats_df['BB+HBP']) / stats_df['PA']
    stats_df['TB'] = stats_df['1B'] + 2*stats_df['2B'] + 3*stats_df['3B'] + 4*stats_df['HR']
    stats_df['SLG'] = stats_df['TB'] / stats_df['AB']
    stats_df['OPS'] = stats_df['OBP'] + stats_df['SLG']
    return stats_df

def main():
    st.title("⚾ NPB打順シミュレーター")
    st.write("このアプリケーションは、NPBの実際の選手成績データに基づき、最も得点効率の良い打順を探索します。任意の打順でのシミュレーションや、最良打順の推定が可能です。")

    st.sidebar.title("📊 シミュレーション設定")
    year = st.sidebar.selectbox("年度を選択", list(range(2022, 2026)), index=2)

    teams = {
        "セントラル・リーグ": ["ヤクルト", "DeNA", "阪神", "巨人", "広島", "中日"],
        "パシフィック・リーグ": ["オリックス", "ソフトバンク", "西武", "楽天", "ロッテ", "日本ハム"]
    }
    league = st.sidebar.selectbox("リーグを選択", list(teams.keys()))
    team = st.sidebar.selectbox("チームを選択", teams[league])

    st.sidebar.title("🔍 最良打順推定設定")
    num_trials = st.sidebar.number_input("試行回数", min_value=10, max_value=10000, value=100, help="ランダムな打順を生成し、シミュレーションを行う回数です。数値を増やすほど精度が向上しますが、時間がかかります。")
    #run_best_order_estimation = st.sidebar.button("最良打順を推定して表示")

    df = load_data(year, team)

    if not df.empty:
        # 選手一覧セクション
        st.markdown("---")
        st.header(f"⚾ {year}年 {team} 選手一覧")
        st.dataframe(df)

        # 任意の打順シミュレーションセクション
        st.markdown("---")
        st.header("📝 任意の打順でシミュレーション")
        st.write("選択したチームの選手を自由に打順に配置し、1試合のシミュレーションを実行します。")
        player_names = df['Player'].tolist()
        batting_order_players = []
        cols = st.columns(3)
        for i in range(1, 10):
            with cols[(i-1)%3]:
                selected_player = st.selectbox(f"{i}番打者", player_names, index=i-1 if i-1 < len(player_names) else 0, key=f"player_{i}")
                batting_order_players.append(selected_player)
        
        if st.button("⚾ 1試合シミュレーション実行"):
            # 選択された選手がデータフレームに存在するか確認
            missing_players = [p for p in batting_order_players if p not in df['Player'].tolist()]
            if missing_players:
                st.error(f"エラー: 以下の選手データが見つかりません。選択し直してください: {', '.join(missing_players)}")
            else:
                batting_order_df = df[df['Player'].isin(batting_order_players)].set_index('Player')
                batting_order_df = batting_order_df.loc[batting_order_players].reset_index()

                result = simulate_game(batting_order_df, enable_inning_log=True)

                st.subheader("📊 シミュレーション結果")
                st.metric("総得点", f"{result['total_runs']}点")

                with st.expander("イニングごとの詳細なプレイログを見る"):
                    inning_log_df = pd.DataFrame(result['inning_log']).T
                    inning_log_df.columns = [f"{i}回" for i in range(1, 10)]
                    inning_log_df.index = [f"{i+1}番: {name}" for i, name in enumerate(batting_order_players)]
                    st.dataframe(inning_log_df)

                st.subheader("📈 打者別成績")
                game_log_df = pd.DataFrame(result['game_log']).T
                game_log_df['Player'] = batting_order_players
                game_log_df['Order'] = range(1, 10)
                game_log_df = game_log_df.set_index(['Order', 'Player'])
                st.dataframe(game_log_df)

        # 最良打順推定結果セクション
        st.markdown("---")
        #if run_best_order_estimation:
        if st.button("最良打順シミュレーション"):
            st.header("🏆 最良打順推定結果")
            st.write("選択された9人の選手の中から、最も得点効率の良い打順と悪い打順を推定します。")
            if len(batting_order_players) < 9:
                st.error("最良打順を推定するには、任意の打順で9人の選手を選択してください。")
            else:
                selected_players_for_estimation = df[df['Player'].isin(batting_order_players)].set_index('Player').loc[batting_order_players].reset_index()

                with st.spinner('⚾ シミュレーションを実行中... (時間がかかる場合があります)'):
                    progress_bar = st.progress(0)
                    estimation_result = estimate_best_batting_order(selected_players_for_estimation, num_trials, progress_bar)
                
                if estimation_result:
                    st.subheader("✨ 最も得点効率の良い打順 (Best Order)")
                    st.metric("平均得点 (1試合あたり)", f"{estimation_result['best_order']['avg_runs']:.2f}点")
                    st.metric("シーズン総得点 (143試合)", f"{estimation_result['best_order']['total_runs']:.0f}点")
                    best_order_df = estimation_result['best_order']['order_df']
                    
                    st.subheader("📊 最良打順 選手別成績")
                    best_stats_df = pd.DataFrame(estimation_result['best_order']['stats']).T
                    best_stats_df['Player'] = best_order_df['Player'].tolist()
                    best_stats_df['Order'] = range(1, 10)
                    best_stats_df = best_stats_df.set_index(['Order', 'Player'])
                    
                    best_stats_df = calculate_player_stats(best_stats_df)

                    st.dataframe(best_stats_df[['PA', 'AB', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'BB+HBP', 'SO', 'Sacrifice_Success', 'Out', 'AVG', 'OBP', 'SLG', 'OPS']].fillna(0).round(3))

                    st.subheader("💔 最も得点効率の悪い打順 (Worst Order)")
                    st.metric("平均得点 (1試合あたり)", f"{estimation_result['worst_order']['avg_runs']:.2f}点")
                    st.metric("シーズン総得点 (143試合)", f"{estimation_result['worst_order']['total_runs']:.0f}点")
                    worst_order_df = estimation_result['worst_order']['order_df']
                    
                    st.subheader("📊 最悪打順 選手別成績")
                    worst_stats_df = pd.DataFrame(estimation_result['worst_order']['stats']).T
                    worst_stats_df['Player'] = worst_order_df['Player'].tolist()
                    worst_stats_df['Order'] = range(1, 10)
                    worst_stats_df = worst_stats_df.set_index(['Order', 'Player'])

                    worst_stats_df = calculate_player_stats(worst_stats_df)

                    st.dataframe(worst_stats_df[['PA', 'AB', 'H', '1B', '2B', '3B', 'HR', 'RBI', 'BB+HBP', 'SO', 'Sacrifice_Success', 'Out', 'AVG', 'OBP', 'SLG', 'OPS']].fillna(0).round(3))
                else:
                    st.error("シミュレーション結果を取得できませんでした。")

if __name__ == "__main__":
    main()