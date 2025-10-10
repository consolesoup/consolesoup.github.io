var WatchListData = null;
var filterTags = [];
document.addEventListener('DOMContentLoaded', LoadWatchListData);

function LoadWatchListData() {
    const watchListSection = document.getElementById('watchlist');
    watchListSection.innerHTML = '<p>データ読み込み中...</p>';

    // URLパラメータからフィルタリングパラメータ取得
    const urlParams = new URLSearchParams(window.location.search);
    filterTags = urlParams.getAll('tag'); 
    FooterBarLayout();

    // Json取得
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

function FooterBarLayout() {
    const footerBar = document.getElementById('footer-bar');
    footerBar.innerHTML = ''; // 内容をクリア

    // filterTags配列の要素数でチェック
    if (filterTags.length > 0) {
        // 複数タグのコンテナ
        const tagsWrapper = document.createElement('div');
        tagsWrapper.classList.add('active-filter-tag-list');
        filterTags.forEach(tag => {
            // タグ全体をラップするコンテナ
            const tagContainer = document.createElement('div');
            tagContainer.classList.add('active-filter-tag');

            // タグのテキスト
            const tagText = document.createElement('span');
            tagText.textContent = tag;
            tagContainer.appendChild(tagText);

            // 解除ボタン (×マーク)
            const clearLink = document.createElement('a');
            clearLink.classList.add('filter-clear-button');
            clearLink.textContent = ' ×';

            // 解除リンクのURLを生成
            const clearParams = new URLSearchParams();
            filterTags.forEach(t => {
                // 現在のタグ以外をパラメータに残す
                if (t !== tag) {
                    clearParams.append('tag', t);
                }
            });

            // 解除リンクのhrefを設定
            const baseUrl = window.location.origin + window.location.pathname;
            if (clearParams.toString() === '') {
                // 残りのタグがない場合はベースURLへ
                clearLink.href = baseUrl;
            } else {
                // 残りのタグがある場合はパラメータを付けて設定
                clearLink.href = `${baseUrl}?${clearParams.toString()}`;
            }

            tagContainer.appendChild(clearLink);
            tagsWrapper.appendChild(tagContainer);
        });
        footerBar.appendChild(tagsWrapper);
    }
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
    
    const baseUrl = window.location.origin + window.location.pathname;
    
    // パラメータからフィルタリング
    let filteredList = watchList;
    if (filterTags.length > 0) {
        filteredList = watchList.filter(item => {
            if (!Array.isArray(item.tag)) return false;
            return filterTags.every(requiredTag => item.tag.includes(requiredTag));
        });
        
        if (filteredList.length === 0) {
            watchlistSection.innerHTML = `<p>「${filterTag}」に一致する作品は見つかりませんでした。</p>`;
            return;
        }
    }
    
    // 年代別にグループ分け
    const groupedByYear = filteredList.reduce((acc, item) => {
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
            for (const tagStr of item.tag) {
                const tagLink = document.createElement('a');
                tagLink.innerText = tagStr;
                tagLink.classList.add('item-tag');
                if (tagStr === 'おすすめ') {
                    tagLink.classList.add('item-tag-recommend');
                }
                
                // タグが選択中かどうかで分岐
                if (filterTags.includes(tagStr)) {
                    // 選択中のタグの場合、ページを更新しないようにする
                    tagLink.href = `#`;
                    tagLink.onclick = (e) => {
                        e.preventDefault();
                    };
                } else {
                    // 未選択のタグの場合、URLにタグを追加
                    const newParams = new URLSearchParams();
                    filterTags.forEach(t => newParams.append('tag', t));
                    newParams.append('tag', tagStr);

                    // タグが追加されたURLに更新
                    tagLink.href = `${baseUrl}?${newParams.toString()}`;
                    tagLink.onclick = null;
                }
                tagContainer.appendChild(tagLink);
            }
            li.appendChild(tagContainer)
            ul.appendChild(li);
        });
        // 年代ごとのリストをセクションに追加
        watchlistSection.appendChild(ul);
    });
}