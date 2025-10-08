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
    const watchlistSection = document.getElementById('watchlist');
    watchlistSection.innerHTML = ''; // レイアウト初期化

    if (WatchListData == null) {
        watchlistSection.innerHTML = '<p>データを読み込めませんでした。</p>';
        return;
    }

    var watchList = null;
    if ('watchlist' in WatchListData) watchList = WatchListData.watchlist;
    if (watchList == null) {
        watchlistSection.innerHTML = '<p>データが壊れています。</p>';
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

    // ソートされた年代ごとに処理を行う
    sortedYears.forEach(year => {
        const itemsInYear = groupedByYear[year];

        // 年代のヘッダーを作成
        const yearHeader = document.createElement('h3');
        yearHeader.textContent = `${year}年`;
        yearHeader.classList.add('sticky-category');
        watchlistSection.appendChild(yearHeader);

        // 年代ごとのリストを作成
        const ul = document.createElement('ul');

        // その年代の各アイテムをリストに追加
        itemsInYear.forEach(item => {
            // リストアイテム
            const li = document.createElement('li');
            li.classList.add('item-list');

            // タイトル
            const itemTitle = document.createElement('h4');
            itemTitle.textContent = item.title;
            itemTitle.classList.add('item-title');
            li.appendChild(itemTitle);
            
            // コメント
            const commentText = document.createElement('p');
            commentText.textContent = item.comment;
            commentText.classList.add('item-comment');
            li.appendChild(commentText)
            
            // タグ一覧
            const tagContainer = document.createElement('div');
            tagContainer.classList.add('tag-container');
            for (const tag of item.tag) {
                const tagText = document.createElement('span');
                tagText.textContent = tag;
                tagText.classList.add('item-tag');
                tagContainer.appendChild(tagText);
            }
            li.appendChild(tagContainer)
            ul.appendChild(li);
        });
        // 年代ごとのリストをセクションに追加
        watchlistSection.appendChild(ul);
    });
}