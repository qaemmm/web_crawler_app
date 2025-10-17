/**
 * 测试第三方API导入功能
 * 用于验证导入接口是否正常工作
 */

async function testImportWithCorrectData() {
    // 正确的测试数据
    const correctToken = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwYW5nc3QiLCJhY2Nlc3NUeXBlIjoxMSwidXNlclR5cGUiOjIsInVzZXJJZCI6MTc4MjY3MzEzODk0ODcxMDQwMSwiZXhwIjoxNzU0NDQ4MzYyLCJqdGkiOiIwZjdkOTQyOS00ZDgzLTRkYzEtOTI1Zi0yMDEyMWMzNjExYzEifQ.SMrWkvCDipIUhtVHsYsFwRiYbnCpp4UCOr4K0-YqmTA";
    const correctFileIds = [1952610856680304642];
    
    console.log("=== 开始测试导入功能 ===");
    console.log("Token:", correctToken.substring(0, 20) + "...");
    console.log("FileIds:", correctFileIds);
    
    try {
        // 测试生产环境导入
        console.log("\n1. 测试生产环境导入...");
        const productionResult = await testImport(correctFileIds, 'production', correctToken);
        console.log("生产环境导入结果:", productionResult);
        
        // 如果生产环境成功，暂时停止轮询任务状态
        if (productionResult.code === 0 && productionResult.data) {
            const taskId = productionResult.data;
            console.log("任务启动成功，任务ID:", taskId);
            console.log('任务状态查询接口暂未完善，停止轮询');
            
            // 开始轮询任务状态（已注释）
            // await pollTaskStatus(taskId, 'production', correctToken);
        }
        
    } catch (error) {
        console.error("测试失败:", error);
    }
}

async function testImport(fileIds, environment, token) {
    const apiBaseUrl = '/api/third-party';
    const endpoint = environment === 'production' ? '/production/import' : '/test/import';
    
    const requestBody = {
        fileIds: fileIds
    };
    
    console.log("发送导入请求:");
    console.log("- URL:", `${apiBaseUrl}${endpoint}`);
    console.log("- 请求体:", requestBody);
    console.log("- Token:", token.substring(0, 20) + "...");
    
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

async function pollTaskStatus(taskId, environment, token) {
    const apiBaseUrl = '/api/third-party';
    const endpoint = environment === 'production' ? '/production/task/status' : '/test/task/status';
    
    console.log("\n开始轮询任务状态...");
    
    const maxAttempts = 20; // 最多轮询20次
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
                    // 继续轮询
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
    
    // 开始轮询
    poll();
}

// 在浏览器控制台中运行测试
if (typeof window !== 'undefined') {
    window.testImportWithCorrectData = testImportWithCorrectData;
    console.log("测试函数已加载到全局变量: testImportWithCorrectData()");
    console.log("在控制台中运行: testImportWithCorrectData()");
}

// 如果在Node.js环境中运行
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { testImportWithCorrectData, testImport, pollTaskStatus };
}