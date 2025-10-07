document.addEventListener('DOMContentLoaded', () => {
    const watchlistSection = document.getElementById('watchlist');

    // データの読み込み
    fetch('watchlist.json')
        .then(response => {
            // HTTPエラー（404など）をチェック
            if (!response.ok) {
                throw new Error('Network response was not ok: ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            // JSONの 'watchlist' 配列を取得
            const animeList = data.watchlist;

            // データを表示する ul 要素を生成
            const ul = document.createElement('ul');
            ul.classList.add('anime-list');

            // h2 タイトルをセクションに追加
            const h2 = document.createElement('h2');
            h2.textContent = "アニメ視聴済リスト";
            watchlistSection.appendChild(h2);

            // 各アイテムを処理
            animeList.forEach(item => {
                const li = document.createElement('li');

                // CSSクラス（ここでは簡単のため "finished" 固定）
                // 実際のデータにステータス（status）があれば、item.statusなどを使えます
                li.classList.add('anime-item', 'finished');

                // HTMLコンテンツの組み立て
                li.innerHTML = `
                    <h3>${item.title}</h3>
                    <p class="meta">
                        <span>カテゴリ: ${item.category}</span>
                        <span>放送年: ${item.year}</span>
                    </p>
                    <p class="comment">${item.comment}</p>
                `;
                
                ul.appendChild(li);
            });

            // 構築したリストをセクションに追加
            watchlistSection.appendChild(ul);
        })
        .catch(error => {
            console.error('データの読み込みまたは処理中にエラーが発生しました:', error);
            watchlistSection.innerHTML = '<p>データを読み込めませんでした。</p>';
        });
});