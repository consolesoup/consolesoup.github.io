var WatchList = [];
var filterCopyright = null;
var filterTags = [];
var filterKeyword = null;
document.addEventListener('DOMContentLoaded', LoadWatchListData);

function LoadWatchListData() {
    const watchListSection = document.getElementById('watchlist');
    watchListSection.innerHTML = '<p>データリスト読み込み中...</p>';
    
    // URLパラメータからフィルタリングパラメータ取得
    const urlParams = new URLSearchParams(window.location.search);
    filterCopyright = urlParams.get('copyright');
    filterTags = urlParams.getAll('tag');
    filterKeyword = urlParams.get('keyword');
    if (filterKeyword === "") filterKeyword = null;
    FooterBarLayout();
    
    // ファイルパスリスト取得
    _fetchJsonData(`./Data/watchlist.json`, (jsonData) => {
        if (jsonData == null)
        {
            watchListSection.innerHTML = '<p>データリストの読み込みに失敗しました...</p>';
            return;
        }
        // json内のパス配列を順番に取得
        _loadLoopWatchListJson(jsonData);
    })
    
    function _loadLoopWatchListJson(periods) {
        // 配列が空になったら次の処理に移動
        if (!Array.isArray(periods) || periods.length == 0)
        {
            WatchListLayout();
            return;
        }
        
        // 配列からファイル情報を取得
        const data = periods[0];
        const fileTitle = data.title;
        const filePath = data.url.replace("../", "./Data/");
        if (filePath == null) {
            periods.shift();
            _loadLoopWatchListJson(periods);
        }
        
        // ファイル情報からデータ取得
        watchListSection.innerHTML = `<p>${fileTitle}のデータ読み込み中...</p>`;
        _fetchJsonData(filePath, (jsonData) => {
            if (jsonData != null) {
                if (Array.isArray(jsonData)) {
                    WatchList = WatchList.concat(jsonData);
                }
            }
            periods.shift();
            _loadLoopWatchListJson(periods);
        });
    }
    
    function _fetchJsonData(filePath, callback) {
        // Json取得
        fetch(filePath)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                callback(data);
            })
            .catch(error => {
                console.error('WatchlistLoadFailed:', error);
                callback(null);
            });
    }
}

function FooterBarLayout() {
    const footerBar = document.getElementById('footer-bar');
    footerBar.innerHTML = ''; // 内容をクリア
    
    // 検索フォームをラップするコンテナ
    const searchWrapper = document.createElement('div');
    searchWrapper.classList.add('footer-search-wrapper');
    footerBar.appendChild(searchWrapper); // フォームをフッターに追加
    
    // 検索テキストボックス
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.id = 'keyword-search-input';
    searchInput.placeholder = 'キーワード検索...';
    searchInput.value = filterKeyword;
    searchWrapper.appendChild(searchInput);
    
    // 検索ボタン
    const searchButton = document.createElement('button');
    searchButton.textContent = '検索';
    searchButton.id = 'keyword-search-button';
    searchWrapper.appendChild(searchButton);
    searchButton.onclick = () => {
        const newParams = new URLSearchParams();
        
        // 選択中のtagとcopyrightパラメータを追加
        if (filterCopyright != null) newParams.append('copyright', filterCopyright);
        filterTags.forEach(t => newParams.append('tag', t));
        
        // キーワードがあればパラメータに追加
        const keyword = searchInput.value.trim();
        if (keyword != null && keyword !== "") newParams.set('keyword', keyword);
        
        // パラメータから遷移先のURL作成
        let newUrl = window.location.origin + window.location.pathname;
        if (newParams.toString()) newUrl += `?${newParams.toString()}`;
        
        // URLが変わっていたらページを遷移する
        if (window.location.search != newUrl) window.location.href = newUrl;
    };
    
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
    let filteredList = WatchList.filter(contents => {
        // 未視聴のものは含まない
        if (!contents.watch) return false;
        
        // コピーライトフィルタ
        if (filterCopyright != null) {
            if (!Array.isArray(contents.copyright)) return false;
            if (!contents.copyright.includes(filterCopyright)) return false;
        }
        
        // タグフィルタ
        if (filterTags.length > 0) {
            if (!Array.isArray(contents.tag)) return false;
            if (!filterTags.every(requiredTag => contents.tag.includes(requiredTag))) return false;
        }
            
        // キーワードフィルタ
        if (filterKeyword != null) {
            const lowerCaseKeyword = filterKeyword.toLowerCase();
                
            // タイトル、コメントのいずれかにキーワードが含まれているかチェック
            const titleMatch = item.title && item.title.toLowerCase().includes(lowerCaseKeyword);
            const commentMatch = item.comment && item.comment.toLowerCase().includes(lowerCaseKeyword);
                
            // タイトルまたはコメントのどちらも一致しない場合は除外
            if (!titleMatch && !commentMatch) return false;
        }
            
        return true;
    });
    
    if (filteredList.length === 0) {
        const notFoundText = document.createElement('p');
        notFoundText.textContent = `該当する作品は見つかりませんでした。`;
        watchlistSection.appendChild(notFoundText);
        return;
    }
    
    // 年代別にグループ分け
    const groupedByYear = filteredList.reduce((acc, contents) => {
        const start_date = new Date(contents.start_date);
        const year = start_date.getUTCFullYear();
        if (!acc[year]) {
            acc[year] = [];
        }
        acc[year].push(contents);
        return acc;
    }, {});
    
    // 年代を新しい順にソート
    const sortedYears = Object.keys(groupedByYear).sort((a, b) => b - a);
    
    // ソートされた年代ごとに処理を行う
    sortedYears.forEach(year => {
        const contentsInYear = groupedByYear[year];
        
        // 年代のヘッダーを作成
        const yearHeader = document.createElement('h3');
        yearHeader.textContent = `${year}年`;
        yearHeader.classList.add('sticky-category');
        watchlistSection.appendChild(yearHeader);

        // 年代ごとのリストを作成
        const ul = document.createElement('ul');

        // その年代の各コンテンツをリストに追加
        contentsInYear.forEach(contents => {
            // リストアイテム
            const li = document.createElement('li');
            li.classList.add('item-list');

            // タイトル
            const itemTitle = document.createElement('h4');
            itemTitle.textContent = contents.title;
            itemTitle.classList.add('item-title');
            li.appendChild(itemTitle);
            
            // コメント
            const commentText = document.createElement('p');
            commentText.textContent = contents.comment;
            commentText.classList.add('item-comment');
            li.appendChild(commentText)
            
            // タグ一覧
            const tagContainer = document.createElement('div');
            tagContainer.classList.add('tag-container');
            
            // おすすめ追加
            if (contents.favorite) {
                const favoriteLink = document.createElement('a');
                favoriteLink.innerText = "おすすめ";
                favoriteLink.classList.add('item-tag-recommend');
                
                // おすすめが選択中かどうかで分岐
                if (filterTags.includes(favoriteLink.innerText)) {
                    // 選択中のタグの場合、ページを更新しないようにする
                    favoriteLink.href = `#`;
                    favoriteLink.onclick = (e) => {
                        e.preventDefault();
                    };
                } else {
                    // 未選択のタグの場合、URLにタグを追加
                    const newParams = new URLSearchParams();
                    if (filterCopyright != null) newParams.append('copyright', filterCopyright);
                    filterTags.forEach(t => newParams.append('tag', t));
                    newParams.append('tag', favoriteLink.innerText);
                    if (filterKeyword != null) newParams.set('keyword', filterKeyword);
                    
                    // おすすめが追加されたURLに更新
                    favoriteLink.href = `${baseUrl}?${newParams.toString()}`;
                    favoriteLink.onclick = null;
                }
                tagContainer.appendChild(favoriteLink);
            }
            
            // コピーライトを追加
            if (Array.isArray(contents.copyright)) {
                for (const copyrightStr of contents.copyright) {
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
            if (Array.isArray(contents.tag)) {
                for (const tagStr of contents.tag) {
                    const tagLink = document.createElement('a');
                    tagLink.innerText = tagStr;
                    tagLink.classList.add('item-tag');

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