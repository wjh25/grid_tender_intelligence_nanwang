<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Link, Search, Document, MessageBox, Monitor } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchTenderDetail, fetchTenders, type DocumentBlock, type TenderDetail, type TenderListItem } from './api'

type ViewName = 'home' | 'southernList' | 'southernDetail'

const view = ref<ViewName>('home')
const loading = ref(false)
const detailLoading = ref(false)
const keyword = ref('')
const tenders = ref<TenderListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const current = ref<TenderDetail | null>(null)

const offset = computed(() => (page.value - 1) * pageSize.value)
const requirementGroups = computed(() => current.value?.requirements ?? [])

async function loadTenders() {
  loading.value = true
  try {
    const data = await fetchTenders({ q: keyword.value || undefined, limit: pageSize.value, offset: offset.value })
    tenders.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error('南网公告列表加载失败，请检查后端和数据库连接')
  } finally {
    loading.value = false
  }
}

async function openSouthernList() {
  view.value = 'southernList'
  await loadTenders()
}

async function openTender(row: TenderListItem) {
  view.value = 'southernDetail'
  detailLoading.value = true
  current.value = null
  try {
    current.value = await fetchTenderDetail(row.id)
  } catch (error) {
    ElMessage.error('公告详情加载失败')
    view.value = 'southernList'
  } finally {
    detailLoading.value = false
  }
}

function search() {
  page.value = 1
  loadTenders()
}

function tableHeaders(block: DocumentBlock) {
  const value = block.table_json as any
  if (Array.isArray(value?.headers)) return value.headers
  return []
}

function tableRows(block: DocumentBlock) {
  const value = block.table_json as any
  if (Array.isArray(value?.rows)) return value.rows
  if (Array.isArray(value?.data)) return value.data
  if (Array.isArray(value) && Array.isArray(value[0])) return value
  return []
}

function tableLines(block: DocumentBlock) {
  const value = block.table_json as any
  if (Array.isArray(value?.lines)) return value.lines
  return []
}

function hasStructuredTable(block: DocumentBlock) {
  return tableRows(block).length > 0
}

function cellText(value: unknown) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

onMounted(() => {
  view.value = 'home'
})
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div class="logo-area">
        <h1>电网招标情报系统</h1>
        <p>供应链统一服务平台数据看板</p>
      </div>
      <el-tag type="success" effect="light" round size="large">局域网节点</el-tag>
    </header>

    <section v-if="view === 'home'" class="home-grid">
      <el-card class="source-tile active-tile" shadow="hover" @click="openSouthernList">
        <el-icon class="tile-icon" color="#1677ff"><Document /></el-icon>
        <div class="tile-content">
          <span class="tile-title">南方电网招标</span>
          <small class="tile-desc">查看已采集的采购/招标公告和标书要求</small>
        </div>
      </el-card>

      <el-card class="source-tile disabled-tile" shadow="never">
        <el-icon class="tile-icon" color="#a8abb2"><Monitor /></el-icon>
        <div class="tile-content">
          <span class="tile-title">国家电网招标</span>
          <small class="tile-desc">系统暂未开放 / 待接入</small>
        </div>
      </el-card>

      <el-card class="source-tile disabled-tile" shadow="never">
        <el-icon class="tile-icon" color="#a8abb2"><MessageBox /></el-icon>
        <div class="tile-content">
          <span class="tile-title">其他电网招标</span>
          <small class="tile-desc">系统暂未开放 / 待接入</small>
        </div>
      </el-card>
    </section>

    <section v-else-if="view === 'southernList'" class="page-section">
      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="section-head">
            <el-page-header @back="view = 'home'" title="返回首页" content="南方电网招标情况" />
            <div class="searchbar">
              <el-input 
                v-model="keyword" 
                clearable 
                placeholder="搜索标题、项目编号、采购人..." 
                :prefix-icon="Search"
                @keyup.enter="search" 
              />
              <el-button type="primary" @click="search">检索</el-button>
            </div>
          </div>
        </template>

        <el-table 
          v-loading="loading" 
          :data="tenders" 
          stripe 
          border
          height="calc(100vh - 290px)" 
          @row-dblclick="openTender"
          class="custom-table"
        >
          <template #empty>
            <el-empty description="暂无符合条件的招标公告数据" />
          </template>
          <el-table-column prop="publish_date" label="发布日期" width="120" align="center" />
          <el-table-column prop="title" label="公告标题" min-width="360" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="table-link" @click.stop="openTender(row)">{{ row.title }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="project_code" label="项目编号" width="200" show-overflow-tooltip />
          <el-table-column prop="company_name" label="招标单位" width="220" show-overflow-tooltip />
          <el-table-column prop="announcement_type" label="公告类型" width="110" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="row.announcement_type === '招标公告' ? 'primary' : 'info'">
                {{ row.announcement_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="正文块" width="80" align="center">
            <template #default="{ row }">{{ row.block_count }}</template>
          </el-table-column>
          <el-table-column label="要求项" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="warning" v-if="row.requirement_count > 0">{{ row.requirement_count }}</el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right" align="center">
            <template #default="{ row }">
              <el-button type="primary" link @click="openTender(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-row">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            background
            layout="total, prev, pager, next, jumper"
            @current-change="loadTenders"
          />
        </div>
      </el-card>
    </section>

    <section v-else class="page-section">
      <div class="detail-topbar">
        <el-page-header @back="view = 'southernList'" title="返回列表" content="公告详情与抽取分析" />
      </div>

      <div v-loading="detailLoading" class="detail-layout" v-if="current">
        <article class="document-panel el-card is-never-shadow">
          <div class="official-title">
            <h3>{{ current.document.title }}</h3>
            <div class="meta-line">
              <el-tag type="info" size="small">{{ current.document.publish_date || '未记录日期' }}</el-tag>
              <span class="company-text">{{ current.document.company_name || '南方电网供应链统一服务平台' }}</span>
              <el-button v-if="current.document.source_url" tag="a" :href="current.document.source_url" target="_blank" type="primary" link :icon="Link">
                查看官网原文
              </el-button>
            </div>
          </div>

          <div class="blocks">
            <el-empty v-if="!current.blocks.length" description="未提取到正文块" />
            <section v-for="block in current.blocks" :key="block.id" class="doc-block">
              <h4 v-if="block.title" class="block-title">
                <span v-if="block.section_no" class="section-no">{{ block.section_no }}</span>
                {{ block.title }}
              </h4>
              <p v-if="block.text_content" class="block-text">{{ block.text_content }}</p>
              
              <div v-if="hasStructuredTable(block)" class="table-scroll">
                <table class="plain-table">
                  <thead v-if="tableHeaders(block).length">
                    <tr>
                      <th v-for="(header, headerIndex) in tableHeaders(block)" :key="headerIndex">
                        {{ cellText(header) }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rowIndex) in tableRows(block)" :key="rowIndex">
                      <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cellText(cell) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              
              <div v-else-if="tableLines(block).length" class="line-table">
                <div v-for="(line, lineIndex) in tableLines(block)" :key="lineIndex" class="line-item">{{ line }}</div>
              </div>
            </section>
          </div>
        </article>

        <aside class="summary-panel">
          <el-card shadow="never" class="info-card">
            <template #header>
              <div class="card-header">基础信息</div>
            </template>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="项目编号" label-align="right" align="left">{{ current.document.project_code || '-' }}</el-descriptions-item>
              <el-descriptions-item label="项目名称" label-align="right" align="left">{{ current.document.project_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="采购人" label-align="right" align="left">{{ current.document.buyer || '-' }}</el-descriptions-item>
              <el-descriptions-item label="代理机构" label-align="right" align="left">{{ current.document.agency || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never" class="info-card mt-4">
            <template #header>
              <div class="card-header">结构化抽取要求</div>
            </template>
            <el-empty v-if="!requirementGroups.length" description="未提取到核心要求" :image-size="60" />
            <el-collapse class="custom-collapse" v-else>
              <el-collapse-item
                v-for="item in requirementGroups"
                :key="item.id"
                :name="item.id"
              >
                <template #title>
                  <span class="req-title">{{ item.requirement_type || item.requirement_title || `要求 ${item.requirement_order}` }}</span>
                </template>
                <div class="req-content">{{ item.requirement_text || '-' }}</div>
              </el-collapse-item>
            </el-collapse>
          </el-card>
        </aside>
      </div>
      
      <el-backtop :right="40" :bottom="40" />
    </section>
  </main>
</template>