var WatchListData = null;
document.addEventListener('DOMContentLoaded', LoadWatchListData);

function LoadWatchListData() {
    const watchListSection = document.getElementById('watchlist');
    watchListSection.innerHTML = '<p>データ読み込み中...</p>';
    
    fetch('watchlist.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok: ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            WatchListData = data;
            WatchListLayout();
        })
        .catch(error => {
            console.error('WatchlistLoadFailed:', error);
            WatchListLayout();
        });
}

function WatchListLayout() {
    const watchListSection = document.getElementById('watchlist');
    watchListSection.innerHTML = ''; // レイアウト初期化
    
    if (WatchListData == null) {
        watchListSection.innerHTML = '<p>データを読み込めませんでした。</p>';
        return;
    }
    
    // WatchListの取得
    var watchList = null;
    if ('watchlist' in WatchListData) watchList = WatchListData.watchlist;
    if (watchList == null) {
        watchListSection.innerHTML = '<p>データが壊れています。</p>';
        return;
    }
    
    // 年代別にグループ分け
    const groupedByYear = watchList.reduce((acc, item) => {
        const year = item.year;
        if (!acc[year]) {
            acc[year] = [];
        }
        acc[year].push(item);
        return acc;
    }, {});
    
    // 年代を新しい順にソート
    const sortedYears = Object.keys(groupedByYear).sort((a, b) => b - a);
    
    // h2タイトルをセクションに追加
    const h2 = document.createElement('h2');
    h2.textContent = "視聴済リスト";
    watchListSection.appendChild(h2);
    
    // ソートされた年代ごとに処理を行う
    sortedYears.forEach(year => {
        const itemsInYear = groupedByYear[year];

        // 年代のヘッダーを作成
        const yearHeader = document.createElement('h3');
        yearHeader.textContent = `--- ${year}年 放送/開始 ---`;
        yearHeader.classList.add('year-separator');
        watchListSection.appendChild(yearHeader);

        // 年代ごとのリストを作成
        const ul = document.createElement('ul');
        ul.classList.add('anime-list');

        // その年代の各アイテムをリストに追加
        itemsInYear.forEach(item => {
            const li = document.createElement('li');
            li.classList.add('anime-item', 'finished');

            li.innerHTML = `
                <div class="category-vertical">${item.category}</div>
                <div class="content-wrapper">
                    <h4 class="item-title">${item.title}</h4>
                    <p class="comment">${item.comment}</p>
                </div>
            `;

            ul.appendChild(li);
        });

        // 年代ごとのリストをセクションに追加
        watchListSection.appendChild(ul);
    });
}