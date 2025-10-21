var WatchList = [];
var filterCopyright = null;
var filterTags = [];
var filterKeyword = null;
document.addEventListener('DOMContentLoaded', LoadWatchListData);

function LoadWatchListData() {
    const watchListSection = document.getElementById('watchlist');
    watchListSection.innerHTML = '<p>データ読み込み中...</p>';
    
    // URLパラメータからフィルタリングパラメータ取得
    const urlParams = new URLSearchParams(window.location.search);
    filterCopyright = urlParams.get('copyright');
    filterTags = urlParams.getAll('tag');
    filterKeyword = urlParams.get('keyword');
    if (filterKeyword === "") filterKeyword = null;
    FooterBarLayout();
    
    // 分割Jsonデータ取得
    _loadLoopWatchListJson([
        '2005-2009',
        '2000-2004',
        '1990-1999',
        '1980-1989',
        '1970-1979',
        '1950-1969',
    ]);
    
    function _loadLoopWatchListJson(periods) {
        if (!Array.isArray(periods) || periods.length == 0)
        {
            WatchListLayout();
            return;
        }
        watchListSection.innerHTML = `<p>${periods[0]}年のデータ読み込み中...</p>`;
        _loadWatchListJson(`./Data/watchlist_${periods[0]}.json`, () => {
            periods.shift();
            _loadLoopWatchListJson(periods);
        });
    }
    
    function _loadWatchListJson(filePath, callback) {
        // Json取得
        fetch(filePath)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                // Jsonに要素があり配列なら追加する
                if ('watchlist' in data) {
                    if (Array.isArray(data.watchlist)) {
                        WatchList = data.watchlist.concat(WatchList);
                    }
                }
                callback();
            })
            .catch(error => {
                console.error('WatchlistLoadFailed:', error);
                callback();
            });
    }
}

function FooterBarLayout() {
    const footerBar = document.getElementById('footer-bar');
    footerBar.innerHTML = ''; // 内容をクリア
    
    // filterTags配列の要素数でチェック
    if (filterTags.length > 0 || filterCopyright != null) {
        // 複数のフィルタリングのコンテナ
        const tagsWrapper = document.createElement('div');
        tagsWrapper.classList.add('active-filter-tag-list');
        footerBar.appendChild(tagsWrapper);
        
        // コピーライトフィルタが設定されている場合
        if (filterCopyright != null) {
            // コピーライト全体をラップするコンテナ
            const copyrightContainer = document.createElement('a');
            copyrightContainer.classList.add('active-filter-tag');
            tagsWrapper.appendChild(copyrightContainer);

            // 解除リンクのURLを生成（選択中のタグだけのパラメータ）
            const clearParams = new URLSearchParams();
            filterTags.forEach(t => {
                clearParams.append('tag', t);
            });
            if (filterKeyword != null) clearParams.set('keyword', filterKeyword);
            
            // 解除リンクのhrefを設定
            const baseUrl = window.location.origin + window.location.pathname;
            if (clearParams.toString() === '') {
                // パラメータがない場合はベースURLへ
                copyrightContainer.href = baseUrl;
            } else {
                // パラメータがある場合はパラメータを付けて設定
                copyrightContainer.href = `${baseUrl}?${clearParams.toString()}`;
            }
            
            // コピーライトのテキスト
            const copyrightText = document.createElement('span');
            copyrightText.textContent = `${filterCopyright} ×`;
            copyrightContainer.appendChild(copyrightText);
        }
        
        // タグフィルタが設定されている場合
        filterTags.forEach(tag => {
            // タグ全体をラップするコンテナ
            const tagContainer = document.createElement('a');
            tagContainer.classList.add('active-filter-tag');
            tagsWrapper.appendChild(tagContainer);
            
            // 解除リンクのURLを生成（選択されたタグがないパラメータ）
            const clearParams = new URLSearchParams();
            if (filterCopyright != null) clearParams.append('copyright', filterCopyright);
            filterTags.forEach(t => {
                if (t !== tag) {
                    clearParams.append('tag', t);
                }
            });
            if (filterKeyword != null) clearParams.set('keyword', filterKeyword);
            
            // 解除リンクのhrefを設定
            const baseUrl = window.location.origin + window.location.pathname;
            if (clearParams.toString() === '') {
                // パラメータがない場合はベースURLへ
                tagContainer.href = baseUrl;
            } else {
                // パラメータがある場合はパラメータを付けて設定
                tagContainer.href = `${baseUrl}?${clearParams.toString()}`;
            }

            // タグのテキスト
            const tagText = document.createElement('span');
            tagText.textContent = `${tag} ×`;
            tagContainer.appendChild(tagText);
        });
    }
}

function WatchListLayout() {
    const watchlistSection = document.getElementById('watchlist');
    watchlistSection.innerHTML = ''; // レイアウト初期化

    if (WatchList == null || WatchList.length === 0) {
        watchlistSection.innerHTML = '<p>データを読み込めませんでした。</p>';
        return;
    }
    
    const baseUrl = window.location.origin + window.location.pathname;
    
    // パラメータからフィルタリング
    let filteredList = WatchList;
    if (filterTags.length > 0 || filterCopyright != null) {
        filteredList = WatchList.filter(item => {
            // コピーライトフィルタ
            if (filterCopyright != null) {
                if (!Array.isArray(item.copyright)) return false;
                if (!item.copyright.includes(filterCopyright)) return false;
            }
            
            // タグフィルタ
            if (!Array.isArray(item.tag)) return false;
            
            // キーワードフィルタ
            if (filterKeyword != null) {
                const lowerCaseKeyword = filterKeyword.toLowerCase();
                
                // タイトル、コメントのいずれかにキーワードが含まれているかチェック
                const titleMatch = item.title && item.title.toLowerCase().includes(lowerCaseKeyword);
                const commentMatch = item.comment && item.comment.toLowerCase().includes(lowerCaseKeyword);
                
                // タイトルまたはコメントのどちらも一致しない場合は除外
                if (!titleMatch && !commentMatch) return false;
            }
            
            return filterTags.every(requiredTag => item.tag.includes(requiredTag));
        });
        
        if (filteredList.length === 0) {
            const notFoundText = document.createElement('p');
            notFoundText.textContent = "";
            if (filterCopyright != null) {
                if (filterTags.length > 0) {
                    notFoundText.textContent = `「${filterTags.join(' / ')}」のタグ全てに一致する「${filterCopyright}」の作品は見つかりませんでした。`;
                } else {
                    notFoundText.textContent = `「${filterCopyright}」の作品は見つかりませんでした。`;
                }
            }
            else notFoundText.textContent += `「${filterTags.join(' / ')}」のタグ全てに一致する作品は見つかりませんでした。`;
            watchlistSection.appendChild(notFoundText);
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
            
            // コピーライトを追加
            if (Array.isArray(item.copyright)) {
                for (const copyrightStr of item.copyright) {
                    const copyrightLink = document.createElement('a');
                    copyrightLink.innerText = copyrightStr;
                    copyrightLink.classList.add('item-copyright');
                    
                    const filterValue = copyrightStr;

                    if (filterCopyright === copyrightStr) {
                        // 選択中の場合、ページを更新しないようにする
                        copyrightLink.href = `#`;
                        copyrightLink.onclick = (e) => { e.preventDefault(); };
                    } else {
                        // 未選択の場合、URLにパラメータを追加
                        const newParams = new URLSearchParams();
                        newParams.append('copyright', copyrightStr);
                        filterTags.forEach(t => {
                            newParams.append('tag', t);
                        });
                        if (filterKeyword != null) newParams.set('keyword', filterKeyword);
                        
                        // リンク先を設定
                        copyrightLink.href = `${baseUrl}?${newParams.toString()}`;
                        copyrightLink.onclick = null;
                    }
                    tagContainer.appendChild(copyrightLink);
                }
            }
            
            // タグの追加
            if (Array.isArray(item.tag)) {
                for (const tagStr of item.tag) {
                    const tagLink = document.createElement('a');
                    tagLink.innerText = tagStr;
                    if (tagStr === 'おすすめ') tagLink.classList.add('item-tag-recommend');
                    else tagLink.classList.add('item-tag');

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
                        if (filterCopyright != null) newParams.append('copyright', filterCopyright);
                        filterTags.forEach(t => newParams.append('tag', t));
                        newParams.append('tag', tagStr);
                        if (filterKeyword != null) newParams.set('keyword', filterKeyword);
                        
                        // タグが追加されたURLに更新
                        tagLink.href = `${baseUrl}?${newParams.toString()}`;
                        tagLink.onclick = null;
                    }
                    tagContainer.appendChild(tagLink);
                }
            }
            
            li.appendChild(tagContainer)
            ul.appendChild(li);
        });
        // 年代ごとのリストをセクションに追加
        watchlistSection.appendChild(ul);
    });
}