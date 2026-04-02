<script setup lang="ts">
</script>

<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <el-icon :size="28" class="logo-icon"><Headset /></el-icon>
        <span class="app-title">xspy</span>
        <span class="app-subtitle">小说自动配音系统</span>
      </div>
      <el-menu mode="horizontal" :ellipsis="false" router class="header-nav">
        <el-menu-item index="/novels">
          <el-icon><Document /></el-icon>小说管理
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><Monitor /></el-icon>任务监控
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style>
:root {
  --header-height: 60px;
}
body {
  margin: 0;
  font-family: 'Inter', 'PingFang SC', -apple-system, sans-serif;
  background: #f5f7fa;
}
.app-container {
  min-height: 100vh;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: var(--header-height);
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.logo-icon {
  color: #409eff;
}
.app-title {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  letter-spacing: -0.5px;
}
.app-subtitle {
  font-size: 13px;
  color: #909399;
  margin-left: 4px;
}
.header-nav {
  border-bottom: none !important;
}
.app-main {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}
</style>
