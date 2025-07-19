import sys
import os
import pandas as pd

# プロジェクトのルートディレクトリをPythonのパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.get_default_lineup import get_default_lineup

# テスト用のダミーHTMLファイルパス
DUMMY_HTML_FILE = "./tests/dummy_html/kiyou_m.html"

def test_get_default_lineup_pacific():
    """パ・リーグのデフォルトスタメン抽出テスト"""
    # ロッテ (M) の2024年パ・リーグのデータを使用
    lineup = get_default_lineup(year="2023", league="Pacific", team_abbr="M")

    print("\n--- Default Lineup (Pacific) ---")
    print(lineup)

    # 期待される結果の検証 (提供されたHTMLとロジックに基づく)
    assert isinstance(lineup, dict)
    assert len(lineup) == 9 # パ・リーグは9ポジション

    # 各ポジションの最多出場選手が正しく抽出されているか
    assert lineup['捕'] == '田村龍弘' # 67試合
    assert lineup['一'] == '山口航輝' # 61試合
    assert lineup['二'] == '中村奨吾' # 133試合
    assert lineup['三'] == '安田尚憲' # 101試合
    assert lineup['遊'] == '藤岡裕大' # 84試合
    assert lineup['左'] == '角中勝也' # 46試合
    assert lineup['中'] == '藤原恭大' # 88試合
    assert lineup['右'] == '荻野貴司' # 49試合
    assert lineup['指'] == 'ポランコ' # 108試合

    # 重複選手が正しく処理されているか
    # 例: 池田来翔は一塁(15), 二塁(2), 三塁(5)だが、一塁は山口航輝が最多なので選ばれない
    assert '池田来翔' not in lineup.values()

    print("✅ test_get_default_lineup_pacific passed.")

def test_get_default_lineup_central():
    """セ・リーグのデフォルトスタメン抽出テスト (DHなし) """
    # 巨人 (G) の2023年セ・リーグのデータを使用
    # 実際のURL: https://nf3.sakura.ne.jp/2023/Central/G/t/kiyou.htm
    lineup = get_default_lineup(year="2023", league="Central", team_abbr="G")

    print("\n--- Default Lineup (Central) ---")
    print(lineup)

    assert isinstance(lineup, dict)
    assert len(lineup) == 8 # セ・リーグは8ポジション (DHなし)
    assert '指' not in lineup # DHが含まれていないこと

    # 巨人の2023年のデータに基づく期待値 (簡易的な確認)
    assert '捕' in lineup
    assert '一' in lineup
    assert '二' in lineup
    assert '三' in lineup
    assert '遊' in lineup
    assert '左' in lineup
    assert '中' in lineup
    assert '右' in lineup

    print("✅ test_get_default_lineup_central passed.")

if __name__ == "__main__":
    test_get_default_lineup_pacific()
    test_get_default_lineup_central()
