// 全局状态管理
const AppState = {
    templates: {},
    currentTemplate: null,
    isGenerating: false
};

// API配置
const API_BASE = '/api';

// 工具函数
const Utils = {
    // 显示状态消息
    showStatus(elementId, message, type = 'info') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = type === 'loading' ?
                `<span class="loading"></span>${message}` : message;
            element.className = `status ${type}`;
        }
    },

    // 显示错误消息
    showError(message) {
        alert(`错误: ${message}`);
        console.error(message);
    },

    // 格式化JSON
    formatJSON(obj) {
        return JSON.stringify(obj, null, 2);
    },

    // 解析JSON
    parseJSON(str) {
        try {
            return JSON.parse(str);
        } catch (e) {
            throw new Error(`JSON格式错误: ${e.message}`);
        }
    },

    // 复制到剪贴板
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            alert('已复制到剪贴板');
        } catch (err) {
            console.error('复制失败:', err);
            alert('复制失败，请手动复制');
        }
    }
};

// 标签页管理
class TabManager {
    constructor() {
        this.initTabs();
    }

    initTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.dataset.tab;

                // 更新按钮状态
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // 更新内容显示
                tabContents.forEach(content => {
                    content.classList.remove('active');
                    if (content.id === targetTab) {
                        content.classList.add('active');
                    }
                });

                // 标签页切换时的特殊处理
                if (targetTab === 'template') {
                    TemplateManager.loadTemplates();
                } else if (targetTab === 'generate') {
                    NovelGenerator.loadTemplatesForGeneration();
                }
            });
        });
    }
}

// 模版管理器
class TemplateManager {
    constructor() {
        this.initEvents();
        this.loadTemplates();
    }

    initEvents() {
        // 模版选择
        document.getElementById('templateSelect').addEventListener('change', (e) => {
            this.selectTemplate(e.target.value);
        });

        // 新建模版
        document.getElementById('newTemplateBtn').addEventListener('click', () => {
            this.newTemplate();
        });

        // 保存模版
        document.getElementById('saveTemplateBtn').addEventListener('click', () => {
            this.saveTemplate();
        });

        // 预览模版
        document.getElementById('previewTemplateBtn').addEventListener('click', () => {
            this.previewTemplate();
        });
    }

    async loadTemplates() {
        try {
            const response = await fetch(`${API_BASE}/templates`);
            if (!response.ok) throw new Error('加载模版失败');

            const data = await response.json();
            AppState.templates = data.templates || {};

            this.updateTemplateSelect();
        } catch (error) {
            Utils.showError(`加载模版失败: ${error.message}`);
        }
    }

    updateTemplateSelect() {
        const select = document.getElementById('templateSelect');
        const genSelect = document.getElementById('genTemplateSelect');

        // 清空选项
        select.innerHTML = '<option value="">选择模版...</option>';
        genSelect.innerHTML = '<option value="">选择模版...</option>';

        // 添加模版选项
        Object.values(AppState.templates).forEach(template => {
            const option = new Option(`${template.name} (${template.id})`, template.id);
            const genOption = new Option(`${template.name} (${template.id})`, template.id);
            select.appendChild(option);
            genSelect.appendChild(genOption.cloneNode(true));
        });
    }

    selectTemplate(templateId) {
        if (!templateId) {
            this.clearEditor();
            return;
        }

        const template = AppState.templates[templateId];
        if (!template) return;

        AppState.currentTemplate = template;
        this.loadTemplateToEditor(template);
        this.showTemplateInfo(template);
    }

    async loadTemplateToEditor(template) {
        try {
            // 加载三个提示词文件内容
            const [writerRole, writingRules, updateStateRules] = await Promise.all([
                this.loadTemplateFile(template.files.writer_role),
                this.loadTemplateFile(template.files.writing_rules),
                this.loadTemplateFile(template.files.update_state_rules)
            ]);

            // 填充编辑器
            document.getElementById('templateId').value = template.id;
            document.getElementById('templateName').value = template.name;
            document.getElementById('templateCategory').value = template.category || '';
            document.getElementById('minWords').value = template.word_count_range?.min || '';
            document.getElementById('maxWords').value = template.word_count_range?.max || '';
            document.getElementById('writerRole').value = writerRole;
            document.getElementById('writingRules').value = writingRules;
            document.getElementById('updateStateRules').value = updateStateRules;

        } catch (error) {
            Utils.showError(`加载模版内容失败: ${error.message}`);
        }
    }

    async loadTemplateFile(filename) {
        try {
            const response = await fetch(`${API_BASE}/template-file/${filename}`);
            if (!response.ok) throw new Error(`加载文件失败: ${filename}`);
            return await response.text();
        } catch (error) {
            console.warn(`加载文件失败: ${filename}`, error);
            return '';
        }
    }

    showTemplateInfo(template) {
        const infoDiv = document.getElementById('templateInfo');
        infoDiv.innerHTML = `
            <h4>${template.name}</h4>
            <p><strong>ID:</strong> ${template.id}</p>
            <p><strong>分类:</strong> ${template.category || '未分类'}</p>
            <p><strong>字数范围:</strong> ${template.word_count_range?.min || 0} - ${template.word_count_range?.max || 0}</p>
            <p><strong>创建时间:</strong> ${template.created_date || '未知'}</p>
        `;
    }

    newTemplate() {
        this.clearEditor();
        // 生成新的模版ID
        const existingIds = Object.keys(AppState.templates).map(id => parseInt(id)).filter(id => !isNaN(id));
        const newId = existingIds.length > 0 ? Math.max(...existingIds) + 1 : 1;
        document.getElementById('templateId').value = String(newId).padStart(3, '0');
    }

    clearEditor() {
        document.getElementById('templateId').value = '';
        document.getElementById('templateName').value = '';
        document.getElementById('templateCategory').value = '';
        document.getElementById('minWords').value = '';
        document.getElementById('maxWords').value = '';
        document.getElementById('writerRole').value = '';
        document.getElementById('writingRules').value = '';
        document.getElementById('updateStateRules').value = '';
        document.getElementById('templateInfo').innerHTML = '';
        AppState.currentTemplate = null;
    }

    async saveTemplate() {
        try {
            const templateData = this.collectTemplateData();

            const response = await fetch(`${API_BASE}/templates`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(templateData)
            });

            if (!response.ok) throw new Error('保存模版失败');

            alert('模版保存成功！');
            await this.loadTemplates();

        } catch (error) {
            Utils.showError(`保存模版失败: ${error.message}`);
        }
    }

    collectTemplateData() {
        const id = document.getElementById('templateId').value.trim();
        const name = document.getElementById('templateName').value.trim();

        if (!id || !name) {
            throw new Error('请填写模版ID和名称');
        }

        return {
            id,
            name,
            category: document.getElementById('templateCategory').value.trim(),
            word_count_range: {
                min: parseInt(document.getElementById('minWords').value) || 2000,
                max: parseInt(document.getElementById('maxWords').value) || 3000
            },
            files: {
                writer_role: `${id}_writer_role.txt`,
                writing_rules: `${id}_writing_rules.txt`,
                update_state_rules: `${id}_update_state_rules.txt`
            },
            contents: {
                writer_role: document.getElementById('writerRole').value.trim(),
                writing_rules: document.getElementById('writingRules').value.trim(),
                update_state_rules: document.getElementById('updateStateRules').value.trim()
            }
        };
    }

    previewTemplate() {
        try {
            const templateData = this.collectTemplateData();
            const preview = `
=== 模版预览 ===
ID: ${templateData.id}
名称: ${templateData.name}
分类: ${templateData.category}
字数范围: ${templateData.word_count_range.min} - ${templateData.word_count_range.max}

=== 角色定义 ===
${templateData.contents.writer_role}

=== 写作规则 ===
${templateData.contents.writing_rules}

=== 状态更新规则 ===
${templateData.contents.update_state_rules}
            `;

            const previewWindow = window.open('', '_blank', 'width=800,height=600');
            previewWindow.document.write(`
                <html>
                <head><title>模版预览</title></head>
                <body style="font-family: monospace; padding: 20px; white-space: pre-wrap;">
                ${preview.replace(/\n/g, '<br>')}
                </body>
                </html>
            `);
        } catch (error) {
            Utils.showError(`预览失败: ${error.message}`);
        }
    }
}

// 小说生成器
class NovelGenerator {
    constructor() {
        this.initEvents();
        this.loadTemplatesForGeneration();
    }

    initEvents() {
        // 生成按钮
        document.getElementById('generateBtn').addEventListener('click', () => {
            this.generateNovel();
        });

        // 复制结果
        document.getElementById('copyResultBtn').addEventListener('click', () => {
            Utils.copyToClipboard(document.getElementById('novelResult').value);
        });



        // 小说ID管理
        document.getElementById('loadNovelBtn').addEventListener('click', () => {
            this.loadNovelInfo();
        });

        document.getElementById('listNovelsBtn').addEventListener('click', () => {
            this.showNovelsList();
        });

        // 小说ID输入框回车事件
        document.getElementById('novelId').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.loadNovelInfo();
            }
        });
    }

    async loadNovelInfo() {
        const novelId = document.getElementById('novelId').value.trim();
        const novelInfo = document.getElementById('novelInfo');

        if (!novelId) {
            this.showNovelInfo('请输入小说ID', 'warning');
            return;
        }

        try {
            // 使用新的完整信息API
            const response = await fetch(`${API_BASE}/novels/${novelId}/info`);
            if (!response.ok) throw new Error('加载失败');

            const result = await response.json();

            if (result.state.found || result.chapters.total_chapters > 0) {
                // 构建详细信息
                const stateChapter = result.state.latest_chapter;
                const fileChapter = result.chapters.latest_chapter_file;
                const syncStatus = result.summary.sync_status;

                let info = `✅ 找到小说: ${novelId}\n`;

                // 章节信息
                if (result.chapters.total_chapters > 0) {
                    info += `📚 章节文件: ${result.chapters.total_chapters}章 (最新: 第${fileChapter}章)\n`;
                } else {
                    info += `📚 章节文件: 无\n`;
                }

                // 状态信息
                if (result.state.found) {
                    info += `📖 状态记录: 第${stateChapter}章\n`;
                    info += `👤 主角: ${result.state.protagonist} (${result.state.level})\n`;
                } else {
                    info += `📖 状态记录: 无\n`;
                }

                // 同步状态
                if (result.chapters.total_chapters > 0 && result.state.found) {
                    const syncIcon = syncStatus === '同步' ? '🟢' : '🟡';
                    info += `${syncIcon} 同步状态: ${syncStatus}\n`;
                }

                // 记忆信息
                if (result.memory.total_messages > 0) {
                    info += `💬 对话记忆: ${result.memory.total_messages}条消息\n`;
                }

                // 世界设定
                if (result.world.has_world_bible) {
                    info += `🌍 世界设定: 已配置\n`;
                }

                // 版本信息
                if (result.versions.has_versions) {
                    info += `📝 多版本: ${result.versions.version_chapters}章有版本`;
                }

                // 剧情摘要
                if (result.state.plot_summary) {
                    const summary = result.state.plot_summary.substring(0, 50);
                    info += `\n📝 剧情: ${summary}...`;
                }

                this.showNovelInfo(info.trim(), 'success');
            } else {
                this.showNovelInfo(`⚠️ 小说 ${novelId} 不存在，将创建新小说`, 'warning');
            }

        } catch (error) {
            this.showNovelInfo(`❌ 加载失败: ${error.message}`, 'error');
        }
    }

    async showNovelsList() {
        try {
            const response = await fetch(`${API_BASE}/novels`);
            if (!response.ok) throw new Error('获取小说列表失败');

            const result = await response.json();
            const novels = result.novels;

            if (novels.length === 0) {
                this.showNovelInfo('📭 暂无小说记录', 'warning');
                return;
            }

            const novelsList = novels.map(id => `📖 ${id}`).join('\n');
            this.showNovelInfo(`📚 现有小说:\n${novelsList}`, 'success');

        } catch (error) {
            this.showNovelInfo(`❌ 获取列表失败: ${error.message}`, 'error');
        }
    }

    showNovelInfo(message, type = 'info') {
        const novelInfo = document.getElementById('novelInfo');
        novelInfo.textContent = message;
        novelInfo.className = `novel-info show ${type}`;

        // 3秒后隐藏（除非是成功状态）
        if (type !== 'success') {
            setTimeout(() => {
                novelInfo.classList.remove('show');
            }, 3000);
        }
    }

    loadTemplatesForGeneration() {
        this.loadTemplatesFromAPI();
    }

    async loadTemplatesFromAPI() {
        try {
            const response = await fetch(`${API_BASE}/templates`);
            if (!response.ok) throw new Error('加载模版失败');

            const data = await response.json();
            AppState.templates = data.templates || {};

            // 更新生成页面的模版选择
            const genSelect = document.getElementById('genTemplateSelect');
            genSelect.innerHTML = '<option value="">选择模版...</option>';

            Object.values(AppState.templates).forEach(template => {
                const option = new Option(`${template.name} (${template.id})`, template.id);
                genSelect.appendChild(option);
            });
        } catch (error) {
            Utils.showError(`加载模版失败: ${error.message}`);
        }
    }

    async generateNovel() {
        if (AppState.isGenerating) return;

        try {
            const generateData = this.collectGenerateData();

            AppState.isGenerating = true;
            document.getElementById('generateBtn').disabled = true;
            Utils.showStatus('generateStatus', '正在生成小说...', 'loading');

            const response = await fetch(`${API_BASE}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(generateData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || '生成失败');
            }

            const result = await response.json();
            document.getElementById('novelResult').value = result.content;

            // 自动保存章节
            const novelId = document.getElementById('novelId').value.trim();
            if (novelId) {
                await this.autoSaveChapter(result.content, novelId);
                Utils.showStatus('generateStatus', '生成完成，已自动保存！', 'success');
            } else {
                Utils.showStatus('generateStatus', '生成完成！', 'success');
            }

        } catch (error) {
            Utils.showError(`生成失败: ${error.message}`);
            Utils.showStatus('generateStatus', '生成失败', 'error');
        } finally {
            AppState.isGenerating = false;
            document.getElementById('generateBtn').disabled = false;
        }
    }

    collectGenerateData() {
        const templateId = document.getElementById('genTemplateSelect').value;
        const chapterOutlineText = document.getElementById('chapterOutline').value.trim();
        const novelId = document.getElementById('novelId').value.trim();

        if (!templateId) {
            throw new Error('请选择模版');
        }

        if (!chapterOutlineText) {
            throw new Error('请输入章节细纲');
        }

        const generateData = {
            template_id: templateId,
            chapter_outline: chapterOutlineText,
            model_name: document.getElementById('modelSelect').value,
            use_memory: document.getElementById('useMemory').checked,
            read_compressed: document.getElementById('readCompressed').checked,
            use_compression: document.getElementById('useCompression').checked,
            use_state: document.getElementById('useState').checked,
            use_world_bible: document.getElementById('useWorldBible').checked,
            update_state: document.getElementById('updateState').checked,
            recent_count: parseInt(document.getElementById('recentCount').value) || 20,
            session_id: novelId || 'default'
        };

        // 添加小说ID（如果有）
        if (novelId) {
            generateData.novel_id = novelId;
        }

        return generateData;
    }

    async autoSaveChapter(content, novelId, chapterIndex = null) {
        try {
            // 如果没有提供章节编号，尝试从细纲中提取
            if (!chapterIndex) {
                const chapterOutline = document.getElementById('chapterOutline').value;
                chapterIndex = this.extractChapterIndex(chapterOutline);
            }

            // 如果仍然没有章节编号，使用默认值1
            if (!chapterIndex) {
                chapterIndex = 1;
            }

            // 调用后端保存API
            const saveData = {
                content: content,
                novel_id: novelId,
                chapter_index: chapterIndex,
                auto_save: true
            };

            const response = await fetch(`${API_BASE}/save-chapter`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(saveData)
            });

            if (!response.ok) {
                throw new Error('自动保存失败');
            }

            const result = await response.json();
            console.log(`章节已保存为: ${result.filename}`);

        } catch (error) {
            console.warn(`自动保存失败: ${error.message}`);
        }
    }

    extractChapterIndex(chapterOutline) {
        // 尝试匹配各种章节索引格式
        const patterns = [
            /第(\d+)章/,  // 第1章、第10章
            /chapter[_\s]*(\d+)/i,  // chapter_1, chapter 1
            /章节[_\s]*(\d+)/,  // 章节_1, 章节 1
            /【第(\d+)章/,  // 【第1章
        ];

        for (const pattern of patterns) {
            const match = chapterOutline.match(pattern);
            if (match) {
                try {
                    return parseInt(match[1]);
                } catch (e) {
                    continue;
                }
            }
        }

        return null;
    }

}

// 对话管理器
class ChatManager {
    constructor() {
        this.initEvents();
    }

    initEvents() {
        // 发送消息
        document.getElementById('sendChatBtn').addEventListener('click', () => {
            this.sendMessage();
        });

        // 回车发送
        document.getElementById('chatInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();

        if (!message) return;

        // 添加用户消息到界面
        this.addMessage('user', message);
        input.value = '';

        try {
            // 获取当前的小说ID作为会话标识
            const novelId = document.getElementById('novelId').value.trim();
            const sessionId = novelId || 'web_chat';  // 如果没有小说ID，使用默认的web_chat

            const response = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    model_name: document.getElementById('chatModel').value,
                    use_memory: document.getElementById('chatMemory').checked,
                    session_id: sessionId  // 使用小说ID作为会话ID
                })
            });

            if (!response.ok) throw new Error('发送消息失败');

            const result = await response.json();
            this.addMessage('assistant', result.response);

        } catch (error) {
            this.addMessage('system', `错误: ${error.message}`);
        }
    }

    addMessage(role, content) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        // 滚动到底部
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// 批量生成管理器
class BatchGenerator {
    constructor() {
        this.isRunning = false;
        this.shouldStop = false;
        this.currentChapter = 0;
        this.totalChapters = 0;
        this.initEvents();
        this.loadTemplatesForBatch();
    }

    initEvents() {
        // 检测进度按钮
        document.getElementById('loadBatchNovelBtn').addEventListener('click', () => {
            this.detectProgress();
        });

        // 开始批量生成
        document.getElementById('startBatchBtn').addEventListener('click', () => {
            this.startBatchGeneration();
        });

        // 停止批量生成
        document.getElementById('stopBatchBtn').addEventListener('click', () => {
            this.stopBatchGeneration();
        });
    }

    async loadTemplatesForBatch() {
        try {
            const response = await fetch(`${API_BASE}/templates`);
            if (!response.ok) throw new Error('获取模版失败');

            const data = await response.json();
            const select = document.getElementById('batchTemplateSelect');

            // 清空现有选项
            select.innerHTML = '<option value="">选择模版...</option>';

            // 添加模版选项
            Object.entries(data.templates).forEach(([id, template]) => {
                const option = document.createElement('option');
                option.value = id;
                option.textContent = `${template.name} (${id})`;
                select.appendChild(option);
            });
        } catch (error) {
            this.addLog(`模版加载失败: ${error.message}`, 'error');
        }
    }

    async detectProgress() {
        const novelId = document.getElementById('batchNovelId').value.trim();
        if (!novelId) {
            alert('请输入小说ID');
            return;
        }

        try {
            // 获取小说信息
            const response = await fetch(`${API_BASE}/novels/${novelId}/info`);
            if (!response.ok) throw new Error('获取小说信息失败');

            const info = await response.json();

            // 显示当前进度
            const maxChapter = info.chapters.latest_chapter_file || 0;
            const nextChapter = maxChapter + 1;

            let infoText = `📊 当前进度：已生成 ${maxChapter} 章\n`;
            infoText += `➡️ 下一章：第 ${nextChapter} 章\n`;
            infoText += `📁 章节文件：${info.chapters.total_chapters} 个\n`;
            infoText += `💾 状态同步：${info.summary.sync_status}\n`;
            infoText += `🧠 记忆分片：${info.memory.total_chunks} 个`;

            this.showBatchInfo(infoText, 'success');
            this.addLog(`检测到小说 ${novelId}，当前已生成 ${maxChapter} 章，下一章为第 ${nextChapter} 章`, 'info');

        } catch (error) {
            this.showBatchInfo(`检测失败: ${error.message}`, 'error');
            this.addLog(`进度检测失败: ${error.message}`, 'error');
        }
    }

    extractMaxChapter(info) {
        // 使用新的API数据结构
        return info.chapters ? info.chapters.latest_chapter_file || 0 : 0;
    }

    async startBatchGeneration() {
        if (this.isRunning) return;

        // 验证输入
        const novelId = document.getElementById('batchNovelId').value.trim();
        const templateId = document.getElementById('batchTemplateSelect').value;
        const chapterCount = parseInt(document.getElementById('batchChapterCount').value);

        if (!novelId) {
            alert('请输入小说ID');
            return;
        }

        if (!templateId) {
            alert('请选择模版');
            return;
        }

        if (!chapterCount || chapterCount < 1) {
            alert('请输入有效的章节数量');
            return;
        }

        try {
            // 检测当前进度
            const response = await fetch(`${API_BASE}/novels/${novelId}/info`);
            if (!response.ok) throw new Error('获取小说信息失败');

            const info = await response.json();
            const currentMaxChapter = this.extractMaxChapter(info);
            const startChapter = currentMaxChapter + 1;

            // 初始化批量生成
            this.isRunning = true;
            this.shouldStop = false;
            this.currentChapter = 0;
            this.totalChapters = chapterCount;

            // 更新UI
            document.getElementById('startBatchBtn').disabled = true;
            document.getElementById('stopBatchBtn').disabled = false;
            this.updateProgress(0, chapterCount);
            this.addLog(`开始批量生成，从第 ${startChapter} 章开始，共生成 ${chapterCount} 章`, 'info');

            // 执行批量生成
            for (let i = 0; i < chapterCount; i++) {
                if (this.shouldStop) {
                    this.addLog('用户手动停止生成', 'warning');
                    break;
                }

                const chapterIndex = startChapter + i;
                this.currentChapter = i + 1;

                try {
                    await this.generateSingleChapter(novelId, templateId, chapterIndex);
                    this.updateProgress(this.currentChapter, this.totalChapters);
                } catch (error) {
                    this.addLog(`第 ${chapterIndex} 章生成失败: ${error.message}`, 'error');
                    break;
                }
            }

            // 完成
            this.addLog('批量生成完成！', 'success');

        } catch (error) {
            this.addLog(`批量生成启动失败: ${error.message}`, 'error');
        } finally {
            this.isRunning = false;
            document.getElementById('startBatchBtn').disabled = false;
            document.getElementById('stopBatchBtn').disabled = true;
        }
    }

    async generateSingleChapter(novelId, templateId, chapterIndex) {
        this.addLog(`正在生成第 ${chapterIndex} 章...`, 'info');

        try {
            // 1. 读取章节细纲
            const outline = await this.loadChapterOutline(novelId, chapterIndex);
            if (!outline) {
                throw new Error(`找不到第 ${chapterIndex} 章的细纲文件`);
            }

            // 2. 收集生成参数
            const generateData = {
                template_id: templateId,
                chapter_outline: outline,
                model_name: document.getElementById('batchModelSelect').value,
                use_memory: document.getElementById('batchUseMemory').checked,
                read_compressed: document.getElementById('batchReadCompressed').checked,
                use_compression: document.getElementById('batchUseCompression').checked,
                use_state: document.getElementById('batchUseState').checked,
                use_world_bible: document.getElementById('batchUseWorldBible').checked,
                update_state: document.getElementById('batchUpdateState').checked,
                recent_count: parseInt(document.getElementById('batchRecentCount').value) || 20,
                session_id: novelId,
                novel_id: novelId
            };

            // 3. 调用生成API
            const response = await fetch(`${API_BASE}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(generateData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || '生成失败');
            }

            const result = await response.json();

            // 4. 自动保存到正确的文件路径
            await this.autoSaveChapter(result.content, novelId, chapterIndex);

            this.addLog(`第 ${chapterIndex} 章生成成功 (${result.word_count} 字)，已自动保存`, 'success');

        } catch (error) {
            this.addLog(`第 ${chapterIndex} 章生成失败: ${error.message}`, 'error');
            throw error;
        }
    }

    async autoSaveChapter(content, novelId, chapterIndex) {
        try {
            // 调用后端保存API，使用正确的文件命名格式
            const saveData = {
                content: content,
                novel_id: novelId,
                chapter_index: chapterIndex,
                auto_save: true  // 标识这是自动保存
            };

            const response = await fetch(`${API_BASE}/save-chapter`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(saveData)
            });

            if (!response.ok) {
                throw new Error('自动保存失败');
            }

            const result = await response.json();
            this.addLog(`章节已保存为: ${result.filename}`, 'info');

        } catch (error) {
            this.addLog(`自动保存失败: ${error.message}`, 'warning');
        }
    }

    async loadChapterOutline(novelId, chapterIndex) {
        try {
            // 构建细纲文件路径
            const outlinePath = `xiaoshuo/zhangjiexigang/${novelId}/${chapterIndex}.txt`;

            // 这里需要后端提供读取细纲文件的API
            // 暂时返回一个默认细纲，实际应该从文件读取
            const response = await fetch(`${API_BASE}/read-outline`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_id: novelId,
                    chapter_index: chapterIndex
                })
            });

            if (response.ok) {
                const data = await response.json();
                return data.outline;
            } else {
                // 如果API不存在，返回默认细纲
                return `【第${chapterIndex}章】\n\n开场：\n- 继续上一章的剧情发展\n\n发展：\n- 推进主线剧情\n\n高潮：\n- 制造冲突和转折\n\n结尾：\n- 为下一章留下悬念\n\n目标字数：2800字`;
            }

        } catch (error) {
            this.addLog(`读取第 ${chapterIndex} 章细纲失败: ${error.message}`, 'warning');
            // 返回默认细纲
            return `【第${chapterIndex}章】\n\n开场：\n- 继续上一章的剧情发展\n\n发展：\n- 推进主线剧情\n\n高潮：\n- 制造冲突和转折\n\n结尾：\n- 为下一章留下悬念\n\n目标字数：2800字`;
        }
    }

    stopBatchGeneration() {
        if (this.isRunning) {
            this.shouldStop = true;
            this.addLog('正在停止批量生成...', 'warning');
        }
    }

    updateProgress(current, total) {
        const percentage = total > 0 ? (current / total) * 100 : 0;
        document.getElementById('progressFill').style.width = `${percentage}%`;
        document.getElementById('progressText').textContent = `进度: ${current}/${total} (${percentage.toFixed(1)}%)`;
    }

    addLog(message, type = 'info') {
        const logContainer = document.getElementById('batchLog');
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;

        const timestamp = new Date().toLocaleTimeString();
        logEntry.textContent = `[${timestamp}] ${message}`;

        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    showBatchInfo(message, type = 'info') {
        const infoDiv = document.getElementById('batchNovelInfo');
        infoDiv.className = `novel-info ${type}`;
        infoDiv.textContent = message;
    }
}

// 应用初始化
document.addEventListener('DOMContentLoaded', () => {
    // 检查API连接
    fetch(`${API_BASE}/health`)
        .then(response => {
            if (!response.ok) {
                throw new Error('API服务未启动');
            }
            console.log('API连接正常');
        })
        .catch(error => {
            Utils.showError(`API连接失败: ${error.message}`);
        });

    // 初始化各个管理器
    new TabManager();
    new TemplateManager();
    new NovelGenerator();
    new ChatManager();
    new BatchGenerator();
    new SettingsManager();

    console.log('小说生成系统前端已启动');
});

// 设定管理器
class SettingsManager {
    constructor() {
        this.currentNovelId = '';
        this.characterVersions = [];
        this.worldVersions = [];
        this.currentCharacterVersion = '';
        this.currentWorldVersion = '';
        this.initEvents();
    }

    initEvents() {
        // 加载设定按钮
        document.getElementById('loadSettingsBtn').addEventListener('click', () => {
            this.loadSettings();
        });

        // 版本选择变化
        document.getElementById('characterVersionSelect').addEventListener('change', (e) => {
            this.loadCharacterSettings(e.target.value);
        });

        document.getElementById('worldVersionSelect').addEventListener('change', (e) => {
            this.loadWorldSettings(e.target.value);
        });

        // 新建按钮
        document.getElementById('newCharacterBtn').addEventListener('click', () => {
            this.createNewCharacterVersion();
        });

        document.getElementById('newWorldBtn').addEventListener('click', () => {
            this.createNewWorldVersion();
        });

        // 保存按钮
        document.getElementById('saveCharacterBtn').addEventListener('click', () => {
            this.saveCharacterSettings();
        });

        document.getElementById('saveWorldBtn').addEventListener('click', () => {
            this.saveWorldSettings();
        });

        // 小说ID输入框回车事件
        document.getElementById('settingsNovelId').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.loadSettings();
            }
        });
    }

    async loadSettings() {
        const novelId = document.getElementById('settingsNovelId').value.trim();
        if (!novelId) {
            this.showSettingsInfo('请输入小说ID', 'warning');
            return;
        }

        this.currentNovelId = novelId;

        try {
            // 获取设定文件列表
            const response = await fetch(`${API_BASE}/settings/${novelId}`);
            if (!response.ok) throw new Error('加载设定失败');

            const result = await response.json();
            this.characterVersions = result.character_versions || [];
            this.worldVersions = result.world_versions || [];

            // 更新版本选择框
            this.updateVersionSelects();

            // 加载最新版本的设定
            if (this.characterVersions.length > 0) {
                const latestCharacter = Math.max(...this.characterVersions.map(v => v.version));
                this.loadCharacterSettings(latestCharacter.toString().padStart(3, '0'));
            }

            if (this.worldVersions.length > 0) {
                const latestWorld = Math.max(...this.worldVersions.map(v => v.version));
                this.loadWorldSettings(latestWorld.toString().padStart(2, '0'));
            }

            this.showSettingsInfo(`✅ 找到小说 ${novelId}\n👤 人物设定: ${this.characterVersions.length}个版本\n🌍 世界设定: ${this.worldVersions.length}个版本`, 'success');

        } catch (error) {
            this.showSettingsInfo(`❌ 加载失败: ${error.message}`, 'error');
        }
    }

    updateVersionSelects() {
        // 更新人物设定版本选择框
        const characterSelect = document.getElementById('characterVersionSelect');
        characterSelect.innerHTML = '<option value="">选择版本...</option>';

        this.characterVersions.forEach(version => {
            const option = new Option(
                `版本 ${version.version.toString().padStart(3, '0')} (${version.filename})`,
                version.version.toString().padStart(3, '0')
            );
            characterSelect.appendChild(option);
        });

        // 更新世界设定版本选择框
        const worldSelect = document.getElementById('worldVersionSelect');
        worldSelect.innerHTML = '<option value="">选择版本...</option>';

        this.worldVersions.forEach(version => {
            const option = new Option(
                `版本 ${version.version.toString().padStart(2, '0')} (${version.filename})`,
                version.version.toString().padStart(2, '0')
            );
            worldSelect.appendChild(option);
        });
    }

    async loadCharacterSettings(version) {
        if (!version || !this.currentNovelId) return;

        try {
            const response = await fetch(`${API_BASE}/settings/${this.currentNovelId}/character/${version}`);
            if (!response.ok) throw new Error('加载人物设定失败');

            const result = await response.json();
            document.getElementById('characterSettings').value = JSON.stringify(result.content, null, 2);
            this.currentCharacterVersion = version;

            // 更新选择框
            document.getElementById('characterVersionSelect').value = version;

        } catch (error) {
            Utils.showError(`加载人物设定失败: ${error.message}`);
        }
    }

    async loadWorldSettings(version) {
        if (!version || !this.currentNovelId) return;

        try {
            const response = await fetch(`${API_BASE}/settings/${this.currentNovelId}/world/${version}`);
            if (!response.ok) throw new Error('加载世界设定失败');

            const result = await response.json();
            document.getElementById('worldSettings').value = JSON.stringify(result.content, null, 2);
            this.currentWorldVersion = version;

            // 更新选择框
            document.getElementById('worldVersionSelect').value = version;

        } catch (error) {
            Utils.showError(`加载世界设定失败: ${error.message}`);
        }
    }

    async createNewCharacterVersion() {
        if (!this.currentNovelId) {
            Utils.showError('请先加载小说设定');
            return;
        }

        try {
            // 获取当前内容
            const currentContent = document.getElementById('characterSettings').value.trim();
            if (!currentContent) {
                Utils.showError('当前没有人物设定内容可复制');
                return;
            }

            // 创建新版本
            const response = await fetch(`${API_BASE}/settings/${this.currentNovelId}/character/new`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: JSON.parse(currentContent),
                    base_version: this.currentCharacterVersion
                })
            });

            if (!response.ok) throw new Error('创建新版本失败');

            const result = await response.json();

            // 重新加载设定列表
            await this.loadSettings();

            // 自动选择新创建的版本
            this.loadCharacterSettings(result.new_version);

            Utils.showStatus('settingsInfo', `✅ 创建人物设定版本 ${result.new_version} 成功`, 'success');

        } catch (error) {
            Utils.showError(`创建新版本失败: ${error.message}`);
        }
    }

    async createNewWorldVersion() {
        if (!this.currentNovelId) {
            Utils.showError('请先加载小说设定');
            return;
        }

        try {
            // 获取当前内容
            const currentContent = document.getElementById('worldSettings').value.trim();
            if (!currentContent) {
                Utils.showError('当前没有世界设定内容可复制');
                return;
            }

            // 创建新版本
            const response = await fetch(`${API_BASE}/settings/${this.currentNovelId}/world/new`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: JSON.parse(currentContent),
                    base_version: this.currentWorldVersion
                })
            });

            if (!response.ok) throw new Error('创建新版本失败');

            const result = await response.json();

            // 重新加载设定列表
            await this.loadSettings();

            // 自动选择新创建的版本
            this.loadWorldSettings(result.new_version);

            Utils.showStatus('settingsInfo', `✅ 创建世界设定版本 ${result.new_version} 成功`, 'success');

        } catch (error) {
            Utils.showError(`创建新版本失败: ${error.message}`);
        }
    }

    async saveCharacterSettings() {
        if (!this.currentNovelId || !this.currentCharacterVersion) {
            Utils.showError('请先选择要保存的版本');
            return;
        }

        try {
            const content = document.getElementById('characterSettings').value.trim();
            if (!content) {
                Utils.showError('人物设定内容不能为空');
                return;
            }

            // 验证JSON格式
            const parsedContent = JSON.parse(content);

            const response = await fetch(`${API_BASE}/settings/${this.currentNovelId}/character/${this.currentCharacterVersion}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: parsedContent })
            });

            if (!response.ok) throw new Error('保存失败');

            Utils.showStatus('settingsInfo', '✅ 人物设定保存成功', 'success');

        } catch (error) {
            if (error instanceof SyntaxError) {
                Utils.showError('JSON格式错误，请检查语法');
            } else {
                Utils.showError(`保存失败: ${error.message}`);
            }
        }
    }

    async saveWorldSettings() {
        if (!this.currentNovelId || !this.currentWorldVersion) {
            Utils.showError('请先选择要保存的版本');
            return;
        }

        try {
            const content = document.getElementById('worldSettings').value.trim();
            if (!content) {
                Utils.showError('世界设定内容不能为空');
                return;
            }

            // 验证JSON格式
            const parsedContent = JSON.parse(content);

            const response = await fetch(`${API_BASE}/settings/${this.currentNovelId}/world/${this.currentWorldVersion}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: parsedContent })
            });

            if (!response.ok) throw new Error('保存失败');

            Utils.showStatus('settingsInfo', '✅ 世界设定保存成功', 'success');

        } catch (error) {
            if (error instanceof SyntaxError) {
                Utils.showError('JSON格式错误，请检查语法');
            } else {
                Utils.showError(`保存失败: ${error.message}`);
            }
        }
    }

    showSettingsInfo(message, type = 'info') {
        const infoDiv = document.getElementById('settingsInfo');
        infoDiv.className = `novel-info show ${type}`;
        infoDiv.textContent = message;

        // 3秒后隐藏（除非是成功状态）
        if (type !== 'success') {
            setTimeout(() => {
                infoDiv.classList.remove('show');
            }, 3000);
        }
    }
} 