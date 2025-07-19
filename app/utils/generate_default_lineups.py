import pandas as pd
import os
import sys

# プロジェクトのルートディレクトリをPythonのパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.utils.get_default_lineup import get_default_lineup

# main.py と同様のチーム略称とリーグ情報
TEAM_ABBREVIATIONS = {
    "ヤクルト": {"abbr": "S", "league": "Central"},
    "DeNA": {"abbr": "DB", "league": "Central"},
    "阪神": {"abbr": "T", "league": "Central"},
    "巨人": {"abbr": "G", "league": "Central"},
    "広島": {"abbr": "C", "league": "Central"},
    "中日": {"abbr": "D", "league": "Central"},
    "オリックス": {"abbr": "B", "league": "Pacific"},
    "ソフトバンク": {"abbr": "H", "league": "Pacific"},
    "西武": {"abbr": "L", "league": "Pacific"},
    "楽天": {"abbr": "E", "league": "Pacific"},
    "ロッテ": {"abbr": "M", "league": "Pacific"},
    "日本ハム": {"abbr": "F", "league": "Pacific"},
}

# get_default_lineup が期待するリーグ名
LEAGUE_MAP = {"Central": "Central", "Pacific": "Pacific"}

def generate_and_save_default_lineups(year: str, output_dir: str = "./data/processed"):
    """
    全球団のデフォルトスタメンを抽出し、CSVファイルとして保存する。

    Args:
        year (str): データを取得する年度。
        output_dir (str): CSVファイルを保存するディレクトリ。
    """
    all_lineups_data = []

    print(f"Generating default lineups for {year}...")

    for team_name, info in TEAM_ABBREVIATIONS.items():
        team_abbr = info["abbr"]
        league_type = info["league"]
        
        print(f"  Processing {team_name} ({league_type})...")

        # get_default_lineupのleague引数は "Pacific" or "Central" を期待
        lineup = get_default_lineup(year=year, league=LEAGUE_MAP[league_type], team_abbr=team_abbr)

        if lineup:
            print(f"    Successfully retrieved lineup for {team_name}.")
            for position, player in lineup.items():
                all_lineups_data.append({
                    "Year": year,
                    "League": league_type,
                    "Team": team_name,
                    "Team_Abbr": team_abbr,
                    "Position": position,
                    "Player": player
                })
        else:
            print(f"    Warning: Could not retrieve lineup for {team_name} ({league_type}).")

    if all_lineups_data:
        df_all_lineups = pd.DataFrame(all_lineups_data)
        
        # カラムの順序を定義
        column_order = ["Year", "League", "Team", "Team_Abbr", "Position", "Player"]
        df_all_lineups = df_all_lineups[column_order]

        output_file = os.path.join(output_dir, f"default_lineups_{year}.csv")
        os.makedirs(output_dir, exist_ok=True)
        df_all_lineups.to_csv(output_file, index=False)
        print(f"Successfully saved default lineups to {output_file}")
    else:
        print("No lineup data generated.")

if __name__ == "__main__":
    # 2022年から2025年までのデータを生成
    for year in range(2022, 2026):
        generate_and_save_default_lineups(year=str(year))
