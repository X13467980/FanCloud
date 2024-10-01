# Wikipedia APIを使ってページIDを取得する
def get_wikipedia_page_id(oshi_name: str) -> str:
    wikipedia_api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': oshi_name,
        'format': 'json'
    }
    
    response = requests.get(wikipedia_api_url, params=params)
    data = response.json()
    
    if 'query' in data and 'search' in data['query']:
        search_results = data['query']['search']
        if search_results:
            # 最初の結果からページIDを取得
            page_id = search_results[0]['pageid']
            return page_id
        else:
            raise HTTPException(status_code=404, detail="Wikipediaの検索結果が見つかりませんでした")
    else:
        raise HTTPException(status_code=500, detail="Wikipedia APIからデータを取得できませんでした")