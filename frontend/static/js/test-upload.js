/**
 * 测试第三方API文件上传功能
 * 用于验证文件上传接口是否正常工作
 */

async function testFileUpload() {
    // 正确的token
    const correctToken = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwYW5nc3QiLCJhYNlc3NUeXBlIjoxMSwidXNlclR5cGUiOjIsInVzZXJJZCI6MTc4MjY3MzEzODk0ODcxMDQwMSwiZXhwIjoxNzU0NDQ4MzYyLCJqdGkiOiIwZjdkOTQyOS00ZDgzLTRkYzEtOTI1Zi0yMDEyMWMzNjExYzEifQ.SMrWkvCDipIUhtVHsYsFwRiYbnCpp4UCOr4K0-YqmTA";
    
    console.log("=== 开始测试文件上传功能 ===");
    console.log("Token:", correctToken.substring(0, 20) + "...");
    
    try {
        // 创建一个测试文件
        const testFile = createTestExcelFile();
        console.log("创建测试文件:", testFile.name, testFile.size, "bytes");
        
        // 测试生产环境上传
        console.log("\n1. 测试生产环境上传...");
        const uploadResult = await uploadFile(testFile, 'production', correctToken);
        console.log("生产环境上传结果:", uploadResult);
        
        if (uploadResult.code === 0 && uploadResult.data) {
            console.log("✅ 文件上传成功!");
            console.log("文件ID:", uploadResult.data.fileId);
            console.log("文件名:", uploadResult.data.fileName);
            
            // 返回fileId用于后续测试
            return uploadResult.data.fileId;
        } else {
            console.error("❌ 文件上传失败:", uploadResult.msg);
            return null;
        }
        
    } catch (error) {
        console.error("测试失败:", error);
        return null;
    }
}

function createTestExcelFile() {
    // 创建一个简单的Excel文件内容（CSV格式）
    const csvContent = `brandName,category,city,phone,address
测试品牌1,测试分类,测试城市,13800138000,测试地址1
测试品牌2,测试分类,测试城市,13800138001,测试地址2
测试品牌3,测试分类,测试城市,13800138002,测试地址3`;
    
    // 创建Blob对象
    const blob = new Blob([csvContent], { type: 'application/vnd.ms-excel' });
    
    // 创建File对象
    const file = new File([blob], 'test_brands.csv', {
        type: 'application/vnd.ms-excel',
        lastModified: Date.now()
    });
    
    return file;
}

async function uploadFile(file, environment, token) {
    const apiBaseUrl = '/api/third-party';
    const endpoint = environment === 'production' ? '/production/upload' : '/test/upload';
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('busSubType', '1001');
    
    console.log("发送上传请求:");
    console.log("- URL:", `${apiBaseUrl}${endpoint}`);
    console.log("- 文件名:", file.name);
    console.log("- 文件大小:", file.size, "bytes");
    console.log("- Token:", token.substring(0, 20) + "...");
    console.log("- busSubType: 1001");
    
    const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        method: 'POST',
        headers: {
            'token': token
        },
        body: formData
    });
    
    console.log("响应状态:", response.status, response.statusText);
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ msg: '网络错误' }));
        console.error("上传接口返回错误:", errorData);
        throw new Error(errorData.msg || `HTTP ${response.status}`);
    }
    
    const result = await response.json();
    console.log("上传接口响应数据:", result);
    
    return result;
}

// 完整测试：上传文件后立即导入
async function testCompleteWorkflow() {
    console.log("=== 开始测试完整工作流程 ===");
    
    try {
        // 1. 测试文件上传
        console.log("\n1. 测试文件上传...");
        const fileId = await testFileUpload();
        
        if (!fileId) {
            console.error("文件上传失败，停止测试");
            return;
        }
        
        // 2. 等待几秒让系统处理文件
        console.log("\n2. 等待系统处理文件...");
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // 3. 测试数据导入
        console.log("\n3. 测试数据导入...");
        const correctToken = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwYW5nc3QiLCJhY2Nlc3NUeXBlIjoxMSwidXNlclR5cGUiOjIsInVzZXJJZCI6MTc4MjY3MzEzODk0ODcxMDQwMSwiZXhwIjoxNzU0NDQ4MzYyLCJqdGkiOiIwZjdkOTQyOS00ZDgzLTRkYzEtOTI1Zi0yMDEyMWMzNjExYzEifQ.SMrWkvCDipIUhtVHsYsFwRiYbnCpp4UCOr4K0-YqmTA";
        
        const importResult = await testImport([fileId], 'production', correctToken);
        console.log("导入结果:", importResult);
        
        if (importResult.code === 0 && importResult.data) {
            const taskId = importResult.data;
            console.log("✅ 完整流程测试成功！任务ID:", taskId);
            
            // 4. 暂时停止轮询任务状态，因为接口还未完善
            console.log('任务状态查询接口暂未完善，停止轮询');
            console.log(`任务已启动，任务ID: ${taskId}`);
            
            // 开始轮询任务状态（已注释）
            // await pollTaskStatus(taskId, 'production', correctToken);
        } else {
            console.error("❌ 导入失败:", importResult.msg);
        }
        
    } catch (error) {
        console.error("完整流程测试失败:", error);
    }
}

// 导入测试函数（复制自test-import.js）
async function testImport(fileIds, environment, token) {
    const apiBaseUrl = '/api/third-party';
    const endpoint = environment === 'production' ? '/production/import' : '/test/import';
    
    const requestBody = {
        fileIds: fileIds
    };
    
    console.log("发送导入请求:");
    console.log("- URL:", `${apiBaseUrl}${endpoint}`);
    console.log("- 请求体:", requestBody);
    
    const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'token': token
        },
        body: JSON.stringify(requestBody)
    });
    
    console.log("响应状态:", response.status, response.statusText);
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ msg: '网络错误' }));
        console.error("导入接口返回错误:", errorData);
        throw new Error(errorData.msg || `HTTP ${response.status}`);
    }
    
    const result = await response.json();
    console.log("导入接口响应数据:", result);
    
    return result;
}

// 任务状态轮询函数（复制自test-import.js）
async function pollTaskStatus(taskId, environment, token) {
    const apiBaseUrl = '/api/third-party';
    const endpoint = environment === 'production' ? '/production/task/status' : '/test/task/status';
    
    console.log("\n开始轮询任务状态...");
    
    const maxAttempts = 20;
    let attempts = 0;
    
    const poll = async () => {
        attempts++;
        console.log(`第${attempts}次查询任务状态...`);
        
        try {
            const response = await fetch(`${apiBaseUrl}${endpoint}?taskId=${taskId}`, {
                headers: {
                    'token': token
                }
            });
            
            if (!response.ok) {
                console.error("查询任务状态失败:", response.status, response.statusText);
                return;
            }
            
            const result = await response.json();
            console.log("任务状态查询结果:", result);
            
            if (result.code === 0) {
                const taskData = result.data;
                console.log(`任务状态: ${taskData.status}, 进度: ${taskData.progress || 0}%`);
                
                if (taskData.status === 'COMPLETED') {
                    console.log("✅ 任务已完成!");
                    console.log(`总数: ${taskData.totalCount || 0}, 成功: ${taskData.successCount || 0}, 失败: ${taskData.failCount || 0}`);
                    return;
                } else if (taskData.status === 'FAILED') {
                    console.log("❌ 任务失败!");
                    console.log("失败原因:", taskData.failReason || '未知错误');
                    return;
                } else if (attempts < maxAttempts) {
                    setTimeout(poll, 3000);
                } else {
                    console.log("⏰ 轮询超时");
                }
            } else {
                console.error("查询任务状态返回错误:", result.msg);
            }
            
        } catch (error) {
            console.error("查询任务状态异常:", error);
        }
    };
    
    poll();
}

// 在浏览器控制台中运行测试
if (typeof window !== 'undefined') {
    window.testFileUpload = testFileUpload;
    window.testCompleteWorkflow = testCompleteWorkflow;
    console.log("测试函数已加载到全局变量:");
    console.log("- testFileUpload(): 测试文件上传");
    console.log("- testCompleteWorkflow(): 测试完整工作流程");
}

// 如果在Node.js环境中运行
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { testFileUpload, testCompleteWorkflow, uploadFile };
}