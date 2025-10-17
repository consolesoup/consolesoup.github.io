var SkillList = [];
var filterSkills = [];
document.addEventListener('DOMContentLoaded', LoadSkillData);

function LoadSkillData() {
    const skillSection = document.getElementById('skill');
    skillSection.innerHTML = '<p>データ読み込み中...</p>';
    
    // URLパラメータからフィルタリングパラメータ取得
    const urlParams = new URLSearchParams(window.location.search);
    filterSkills = urlParams.getAll('skill');
    FooterBarLayout();
    
    // Jsonデータ取得
    _loadSkillListJson('./skill_list.json');
    
    function _loadSkillListJson(filePath) {
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
                if ('skill_list' in data) {
                    if (Array.isArray(data.skill_list)) {
                        SkillList = data.skill_list.concat(SkillList);
                    }
                }
                SkillListLayout();
            })
            .catch(error => {
                console.error('SkillListLoadFailed:', error);
                SkillListLayout();
            });
    }
}

function FooterBarLayout() {
    const footerBar = document.getElementById('footer-bar');
    footerBar.innerHTML = ''; // 内容をクリア
    
    // filterSkills配列の要素数でチェック
    if (filterSkills.length > 0) {
        // 複数のフィルタリングのコンテナ
        const skillsWrapper = document.createElement('div');
        skillsWrapper.classList.add('active-filter-tag-list');
        
        // スキルフィルタが設定されている場合
        filterSkills.forEach(skill => {
            // スキル全体をラップするコンテナ
            const skillContainer = document.createElement('div');
            skillContainer.classList.add('active-filter-tag');
            
            // スキルのテキスト
            const skillText = document.createElement('span');
            skillText.textContent = skill;
            skillContainer.appendChild(skillText);
            
            // 解除ボタン (×マーク)
            const clearLink = document.createElement('a');
            clearLink.classList.add('filter-clear-button');
            clearLink.textContent = ' ×';
            
            // 解除リンクのURLを生成（選択されたスキルがないパラメータ）
            const clearParams = new URLSearchParams();
            filterSkills.forEach(t => {
                if (t !== skill) {
                    clearParams.append('skill', t);
                }
            });
            
            // 解除リンクのhrefを設定
            const baseUrl = window.location.origin + window.location.pathname;
            if (clearParams.toString() === '') {
                // パラメータがない場合はベースURLへ
                clearLink.href = baseUrl;
            } else {
                // パラメータがある場合はパラメータを付けて設定
                clearLink.href = `${baseUrl}?${clearParams.toString()}`;
            }
            
            skillContainer.appendChild(clearLink);
            skillsWrapper.appendChild(skillContainer);
        });
        footerBar.appendChild(skillsWrapper);
    }
}

function SkillListLayout() {
    const skillListSection = document.getElementById('skill');
    skillListSection.innerHTML = ''; // レイアウト初期化

    if (SkillList == null || SkillList.length === 0) {
        skillListSection.innerHTML = '<p>データを読み込めませんでした。</p>';
        return;
    }
    
    const baseUrl = window.location.origin + window.location.pathname;
    
    // カテゴリ別にグループ分け
    const groupedByCategory = SkillList.reduce((acc, item) => {
        // item.category は配列なので、forEachで全てのカテゴリーを処理
        if (Array.isArray(item.category)) {
            item.category.forEach(categoryName => {
                // カテゴリーがまだaccに存在しない場合は、空の配列として初期化
                if (!acc[categoryName]) {
                    acc[categoryName] = [];
                }
                // そのカテゴリーにスキル名 (item.name) を追加
                acc[categoryName].push(item.name);
            });
        }
        return acc;
    }, {});

    // カテゴリのリスト作成
    const categoryList = Object.keys(groupedByCategory);
    
    // 業務スキルのヘッダーを作成
    const skillHeader = document.createElement('h3');
    skillHeader.textContent = '業務スキル';
    skillListSection.appendChild(skillHeader);

    // グループ化されたカテゴリごとに処理を行う
    categoryList.forEach(category => {
        const skillsInCategory = groupedByCategory[category];
        
        // skill-list
        const skillListDiv = document.createElement('div');
        skillListDiv.classList.add('skill-list');
        skillListSection.appendChild(skillListDiv);

        // skill-category
        const skillCategorySpan = document.createElement('span');
        skillCategorySpan.textContent = category;
        skillCategorySpan.classList.add('skill-category');
        skillListDiv.appendChild(skillCategorySpan);

        // item-skill-list
        const itemSkillListDiv = document.createElement('div');
        itemSkillListDiv.classList.add('item-skill-list');
        skillListDiv.appendChild(itemSkillListDiv);

        // そのカテゴリの各スキルをリストに追加
        skillsInCategory.forEach(skill => {
            // item-skill
            const itemSkillLink = document.createElement('a');
            itemSkillLink.textContent = skill;
            itemSkillLink.classList.add('item-skill');
            itemSkillListDiv.appendChild(itemSkillLink);

            // スキルが選択中かどうかで分岐
            if (filterSkills.includes(skill)) {
                // 選択中のスキルの場合、ページを更新しないようにする
                itemSkillLink.href = `#`;
                itemSkillLink.onclick = (e) => {
                    e.preventDefault();
                };
            } else {
                // 未選択のスキルの場合、URLにスキルを追加
                const newParams = new URLSearchParams();
                filterSkills.forEach(t => newParams.append('skill', t));
                newParams.append('skill', skill);
                        
                // スキルが追加されたURLに更新
                itemSkillLink.href = `${baseUrl}?${newParams.toString()}`;
                itemSkillLink.onclick = null;
            }
        });
    });
}