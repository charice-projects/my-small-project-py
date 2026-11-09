/**
 * Omniframe Server - 前端逻辑
 */

class OmniframeClient {
    constructor() {
        this.baseUrl = window.location.origin;
        this.sessionId = null;
        this.commandHistory = [];
        this.currentResults = [];
        this.isLoading = false;
        
        // 初始化
        this.init();
    }
    
    async init() {
        console.log('🚀 Omniframe Client 初始化...');
        
        // 获取会话ID
        await this.getSessionInfo();
        
        // 绑定事件
        this.bindEvents();
        
        // 加载命令历史
        await this.loadCommandHistory();
        
        // 设置自动建议
        this.setupAutocomplete();
        
        // 定期刷新状态
        setInterval(() => this.updateSystemStatus(), 30000);
        
        // 初始状态更新
        await this.updateSystemStatus();
    }
    
    async getSessionInfo() {
        try {
            const response = await this.apiCall('/api/context/status');
            if (response.success) {
                this.sessionId = response.session_id;
                document.getElementById('session-id').textContent = this.sessionId;
                document.getElementById('session-duration').textContent = response.session_duration;
            }
        } catch (error) {
            console.error('获取会话信息失败:', error);
        }
    }
    
    bindEvents() {
        // 执行按钮
        document.getElementById('execute-btn').addEventListener('click', () => this.executeCommand());
        
        // 命令输入框回车
        document.getElementById('command-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.executeCommand();
        });
        
        // 快速命令
        document.querySelectorAll('#quick-commands button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const command = e.target.getAttribute('data-command');
                document.getElementById('command-input').value = command;
                this.executeCommand();
            });
        });
        
        // 清空结果
        document.getElementById('clear-results').addEventListener('click', () => this.clearResults());
        
        // 清除历史
        document.getElementById('clear-history').addEventListener('click', () => this.clearHistory());
        
        // 刷新状态
        document.getElementById('refresh-status').addEventListener('click', () => this.updateSystemStatus());
        
        // 导出结果
        document.getElementById('export-results').addEventListener('click', () => this.exportResults());
        
        // 确认模态框
        document.getElementById('confirm-yes').addEventListener('click', () => this.confirmOperation());
        
        // 初始焦点
        document.getElementById('command-input').focus();
    }
    
    setupAutocomplete() {
        const input = document.getElementById('command-input');
        
        input.addEventListener('input', async (e) => {
            const value = e.target.value;
            if (value.length < 2) return;
            
            try {
                const response = await this.apiCall('/api/commands/suggest', 'POST', {
                    partial_command: value
                });
                
                if (response.success && response.suggestions.length > 0) {
                    // 这里可以集成autocomplete库
                    // 简化处理：只显示第一个建议
                    // console.log('建议:', response.suggestions);
                }
            } catch (error) {
                // 静默失败
            }
        });
    }
    
    async executeCommand() {
        const commandInput = document.getElementById('command-input');
        const command = commandInput.value.trim();
        
        if (!command) {
            this.showMessage('请输入命令', 'warning');
            return;
        }
        
        // 显示加载指示器
        this.showLoading(true);
        
        try {
            const response = await this.apiCall('/api/commands/execute', 'POST', {
                command: command,
                session_id: this.sessionId,
                auto_index: true
            });
            
            // 处理结果
            await this.handleCommandResponse(command, response);
            
            // 清空输入框
            commandInput.value = '';
            
            // 保存到历史记录（前端）
            this.addToHistory(command, response);
            
        } catch (error) {
            this.showMessage(`执行失败: ${error.message}`, 'error');
            console.error('命令执行失败:', error);
        } finally {
            this.showLoading(false);
        }
    }
    
    async handleCommandResponse(command, response) {
        // 隐藏欢迎信息
        document.getElementById('welcome-message').classList.add('d-none');
        
        if (response.requires_confirmation) {
            // 显示确认模态框
            this.showConfirmationModal(command, response);
            return;
        }
        
        if (response.success) {
            // 显示成功结果
            this.displayResults(response);
            
            // 更新结果计数
            this.updateResultCount(response);
            
            // 更新最后执行时间
            this.updateLastExecution(command);
            
            // 如果命令是"初始化索引"等，更新状态
            if (command.includes('索引') || command.includes('index')) {
                await this.updateSystemStatus();
            }
        } else {
            this.showMessage(response.message || '命令执行失败', 'error');
        }
    }
    
    displayResults(response) {
        const container = document.getElementById('results-container');
        
        // 创建结果项
        const resultItem = document.createElement('div');
        resultItem.className = 'result-item success';
        
        const timestamp = new Date().toLocaleTimeString();
        
        let content = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">
                        <i class="bi bi-check-circle text-success"></i>
                        ${response.message || '命令执行成功'}
                    </h6>
                    <small class="text-muted">${timestamp} • 耗时: ${response.execution_time?.toFixed(2)}s</small>
                </div>
                <button class="btn btn-sm btn-outline-secondary btn-action copy-result" 
                        title="复制结果">
                    <i class="bi bi-clipboard"></i>
                </button>
            </div>
        `;
        
        // 如果有数据，显示数据
        if (response.data && response.data.length > 0) {
            content += `<div class="mt-3">`;
            
            if (response.action === 'list' || response.action === 'search') {
                // 文件列表
                content += `<div class="list-group">`;
                response.data.forEach(item => {
                    const icon = item.is_dir ? 'bi-folder' : this.getFileIcon(item.name);
                    
                    content += `
                        <div class="list-group-item list-group-item-action">
                            <div class="d-flex w-100 justify-content-between">
                                <div>
                                    <i class="bi ${icon} me-2"></i>
                                    <strong>${item.name}</strong>
                                </div>
                                <small class="text-muted">${item.size_human}</small>
                            </div>
                            <div class="mt-1">
                                <small class="text-muted">${item.relative_path}</small>
                                <div class="mt-1">
                                    <button class="btn btn-sm btn-outline-primary btn-action" 
                                            onclick="client.downloadFile('${item.path}')">
                                        <i class="bi bi-download"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-info btn-action" 
                                            onclick="client.showFileInfo('${item.path}')">
                                        <i class="bi bi-info-circle"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                });
                content += `</div>`;
            } else if (response.action === 'archive') {
                // 压缩包
                content += `
                    <div class="alert alert-success">
                        <i class="bi bi-file-zip"></i>
                        压缩包已创建: ${response.data[0]?.name || 'archive.zip'}
                        <button class="btn btn-sm btn-success ms-2" 
                                onclick="client.downloadArchive('${response.data[0]?.path}')">
                            下载
                        </button>
                    </div>
                `;
            } else if (response.action === 'system_info') {
                // 系统信息
                content += `<pre class="code-block">${JSON.stringify(response.data, null, 2)}</pre>`;
            }
            
            content += `</div>`;
        }
        
        // 如果有文本输出
        if (response.text_output) {
            content += `<div class="mt-2"><pre class="code-block">${response.text_output}</pre></div>`;
        }
        
        resultItem.innerHTML = content;
        
        // 添加到容器顶部
        container.insertBefore(resultItem, container.firstChild);
        
        // 绑定复制按钮
        resultItem.querySelector('.copy-result')?.addEventListener('click', () => {
            this.copyToClipboard(JSON.stringify(response, null, 2));
            this.showMessage('结果已复制到剪贴板', 'success');
        });
    }
    
    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            'pdf': 'bi-file-earmark-pdf',
            'jpg': 'bi-file-image', 'jpeg': 'bi-file-image', 'png': 'bi-file-image', 'gif': 'bi-file-image',
            'txt': 'bi-file-text', 'md': 'bi-file-text',
            'zip': 'bi-file-zip', 'rar': 'bi-file-zip', '7z': 'bi-file-zip',
            'mp3': 'bi-file-music', 'wav': 'bi-file-music',
            'mp4': 'bi-file-play', 'avi': 'bi-file-play', 'mov': 'bi-file-play',
            'py': 'bi-file-code', 'js': 'bi-file-code', 'html': 'bi-file-code', 'css': 'bi-file-code',
            'exe': 'bi-gear', 'bat': 'bi-terminal'
        };
        
        return icons[ext] || 'bi-file';
    }
    
    showConfirmationModal(command, response) {
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        const messageEl = document.getElementById('confirm-message');
        const detailsEl = document.getElementById('confirm-details');
        
        // 构建确认消息
        let message = `<p>${command}</p>`;
        let details = '';
        
        response.confirmations?.forEach(conf => {
            details += `<div class="mb-1"><i class="bi bi-exclamation-circle"></i> ${conf.message}</div>`;
        });
        
        messageEl.innerHTML = message;
        detailsEl.innerHTML = details;
        
        // 存储当前待确认的操作
        this.pendingConfirmation = { command, response };
        
        modal.show();
    }
    
    async confirmOperation() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('confirmModal'));
        const { command, response } = this.pendingConfirmation;
        
        modal.hide();
        
        // 发送确认请求
        try {
            const confirmResponse = await this.apiCall('/api/commands/confirm', 'POST', {
                confirmation_id: 'pending',
                confirmed: true,
                session_id: this.sessionId
            });
            
            if (confirmResponse.success) {
                // 重新执行命令（实际应该使用存储的响应）
                const commandInput = document.getElementById('command-input');
                commandInput.value = command;
                this.executeCommand();
            }
        } catch (error) {
            this.showMessage(`确认失败: ${error.message}`, 'error');
        }
    }
    
    async loadCommandHistory() {
        try {
            const response = await this.apiCall('/api/commands/history');
            if (response.success) {
                this.displayCommandHistory(response.history);
            }
        } catch (error) {
            console.error('加载历史失败:', error);
        }
    }
    
    displayCommandHistory(history) {
        const container = document.getElementById('command-history');
        container.innerHTML = '';
        
        history.slice(0, 10).forEach(item => {
            const historyItem = document.createElement('a');
            historyItem.href = '#';
            historyItem.className = `list-group-item list-group-item-action history-item ${item.result.success ? 'success' : 'error'}`;
            
            const time = new Date(item.timestamp).toLocaleTimeString();
            
            historyItem.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <small class="text-truncate" title="${item.command}">${item.command}</small>
                    <small class="text-muted">${time}</small>
                </div>
                <small class="text-muted">${item.result.action || 'unknown'}</small>
            `;
            
            historyItem.addEventListener('click', (e) => {
                e.preventDefault();
                document.getElementById('command-input').value = item.command;
                document.getElementById('command-input').focus();
            });
            
            container.appendChild(historyItem);
        });
    }
    
    addToHistory(command, response) {
        const container = document.getElementById('command-history');
        
        const historyItem = document.createElement('a');
        historyItem.href = '#';
        historyItem.className = `list-group-item list-group-item-action history-item ${response.success ? 'success' : 'error'}`;
        
        const time = new Date().toLocaleTimeString();
        
        historyItem.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <small class="text-truncate" title="${command}">${command}</small>
                <small class="text-muted">${time}</small>
            </div>
            <small class="text-muted">${response.action || 'unknown'}</small>
        `;
        
        historyItem.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('command-input').value = command;
            document.getElementById('command-input').focus();
        });
        
        // 添加到顶部
        container.insertBefore(historyItem, container.firstChild);
        
        // 限制历史记录数量
        if (container.children.length > 10) {
            container.removeChild(container.lastChild);
        }
    }
    
    async updateSystemStatus() {
        try {
            // 系统信息
            const systemInfo = await this.apiCall('/system/info');
            if (systemInfo.status === 'success') {
                const cpu = systemInfo.resources.cpu_percent;
                const memory = systemInfo.resources.memory_percent;
                
                // 更新状态指示器（简化）
                const statusEl = document.getElementById('server-status');
                if (cpu > 80 || memory > 80) {
                    statusEl.className = 'badge bg-warning';
                    statusEl.textContent = '高负载';
                } else {
                    statusEl.className = 'badge bg-success';
                    statusEl.textContent = '运行正常';
                }
            }
            
            // 上下文状态
            const contextStatus = await this.apiCall('/api/context/status');
            if (contextStatus.success) {
                document.getElementById('session-duration').textContent = 
                    contextStatus.session_duration;
                
                // 更新命令历史
                this.displayCommandHistory(contextStatus.statistics?.command_history || []);
            }
        } catch (error) {
            console.error('更新状态失败:', error);
            document.getElementById('server-status').className = 'badge bg-danger';
            document.getElementById('server-status').textContent = '断开连接';
        }
    }
    
    showLoading(show) {
        this.isLoading = show;
        const loader = document.getElementById('loading-indicator');
        const executeBtn = document.getElementById('execute-btn');
        
        if (show) {
            loader.classList.remove('d-none');
            executeBtn.disabled = true;
            executeBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 执行中...';
        } else {
            loader.classList.add('d-none');
            executeBtn.disabled = false;
            executeBtn.innerHTML = '<i class="bi bi-play-fill"></i> 执行';
        }
    }
    
    showMessage(message, type = 'info') {
        // 创建临时消息
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.getElementById('results-container');
        container.insertBefore(alert, container.firstChild);
        
        // 3秒后自动消失
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 3000);
    }
    
    clearResults() {
        const container = document.getElementById('results-container');
        container.innerHTML = '';
        document.getElementById('result-count').textContent = '0';
        document.getElementById('welcome-message').classList.remove('d-none');
    }
    
    async clearHistory() {
        try {
            const response = await this.apiCall('/api/context/clear', 'POST', {
                history_type: 'command'
            });
            
            if (response.success) {
                this.displayCommandHistory([]);
                this.showMessage('历史记录已清除', 'success');
            }
        } catch (error) {
            this.showMessage(`清除失败: ${error.message}`, 'error');
        }
    }
    
    updateResultCount(response) {
        const count = response.data?.length || 0;
        document.getElementById('result-count').textContent = count;
    }
    
    updateLastExecution(command) {
        const time = new Date().toLocaleTimeString();
        document.getElementById('last-execution').textContent = `${time}: ${command.substring(0, 30)}${command.length > 30 ? '...' : ''}`;
    }
    
    async exportResults() {
        // 简化实现：导出当前页面内容
        const content = document.getElementById('results-container').innerText;
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `omniframe-results-${new Date().toISOString().slice(0, 10)}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    // 文件操作
    async downloadFile(path) {
        window.open(`${this.baseUrl}/api/files/download?path=${encodeURIComponent(path)}`, '_blank');
    }
    
    async downloadArchive(path) {
        window.open(`${this.baseUrl}/api/files/download?path=${encodeURIComponent(path)}`, '_blank');
    }
    
    async showFileInfo(path) {
        try {
            const response = await this.apiCall(`/api/files/info?path=${encodeURIComponent(path)}`);
            if (response.success) {
                const info = response.info;
                const modalContent = `
                    <div class="modal fade" id="fileInfoModal" tabindex="-1">
                        <div class="modal-dialog modal-lg">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h5 class="modal-title">
                                        <i class="bi bi-info-circle"></i> 文件信息
                                    </h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                </div>
                                <div class="modal-body">
                                    <table class="table table-sm">
                                        <tr><th>名称</th><td>${info.name}</td></tr>
                                        <tr><th>路径</th><td><code>${info.path}</code></td></tr>
                                        <tr><th>大小</th><td>${info.size_human} (${info.size} 字节)</td></tr>
                                        <tr><th>创建时间</th><td>${info.created_iso}</td></tr>
                                        <tr><th>修改时间</th><td>${info.modified_iso}</td></tr>
                                        <tr><th>类型</th><td>${info.is_file ? '文件' : '目录'}</td></tr>
                                        <tr><th>MIME类型</th><td>${info.mime_type}</td></tr>
                                        <tr><th>权限</th><td>${info.permissions}</td></tr>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                // 移除旧的模态框
                const oldModal = document.getElementById('fileInfoModal');
                if (oldModal) oldModal.remove();
                
                // 添加新模态框
                document.body.insertAdjacentHTML('beforeend', modalContent);
                
                // 显示模态框
                const modal = new bootstrap.Modal(document.getElementById('fileInfoModal'));
                modal.show();
            }
        } catch (error) {
            this.showMessage(`获取文件信息失败: ${error.message}`, 'error');
        }
    }
    
    // 工具方法
    async apiCall(endpoint, method = 'GET', data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };
        
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    copyToClipboard(text) {
        navigator.clipboard.writeText(text).catch(err => {
            console.error('复制失败:', err);
        });
    }
}

// 全局客户端实例
let client;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    client = new OmniframeClient();
    window.client = client; // 暴露给全局，便于调试
});