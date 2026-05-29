<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, Link, Search } from '@element-plus/icons-vue'
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
      <div>
        <h1>电网招标情报</h1>
        <p>南方电网公开招标公告内部看板</p>
      </div>
      <el-tag type="success" effect="dark">局域网版本</el-tag>
    </header>

    <section v-if="view === 'home'" class="home-grid">
      <button class="source-tile active" @click="openSouthernList">
        <span>南网招标</span>
        <small>查看已采集公告和标书情况</small>
      </button>
      <button class="source-tile disabled" disabled>
        <span>国网招标</span>
        <small>暂未开放</small>
      </button>
      <button class="source-tile disabled" disabled>
        <span>其他电网招标</span>
        <small>暂未开放</small>
      </button>
    </section>

    <section v-else-if="view === 'southernList'" class="page-section">
      <div class="section-head">
        <div>
          <el-button :icon="ArrowLeft" circle @click="view = 'home'" />
          <h2>南网招标情况</h2>
        </div>
        <div class="searchbar">
          <el-input v-model="keyword" clearable placeholder="标题、项目编号、采购人" @keyup.enter="search" />
          <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tenders" stripe height="calc(100vh - 250px)" @row-dblclick="openTender">
        <el-table-column prop="publish_date" label="发布时间" width="120" />
        <el-table-column prop="title" label="公告标题" min-width="360" show-overflow-tooltip />
        <el-table-column prop="project_code" label="项目编号" width="190" show-overflow-tooltip />
        <el-table-column prop="company_name" label="来源公司" width="220" show-overflow-tooltip />
        <el-table-column prop="announcement_type" label="类型" width="110" />
        <el-table-column label="正文块" width="90">
          <template #default="{ row }">{{ row.block_count }}</template>
        </el-table-column>
        <el-table-column label="要求" width="80">
          <template #default="{ row }">{{ row.requirement_count }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openTender(row)">查看标书情况</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-row">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadTenders"
        />
      </div>
    </section>

    <section v-else class="page-section">
      <div class="section-head">
        <div>
          <el-button :icon="ArrowLeft" circle @click="view = 'southernList'" />
          <h2>南网招标情况</h2>
        </div>
      </div>

      <div v-loading="detailLoading" class="detail-layout" v-if="current">
        <article class="document-panel">
          <div class="official-title">
            <h3>{{ current.document.title }}</h3>
            <div class="meta-line">
              <span>{{ current.document.publish_date || '未记录日期' }}</span>
              <span>{{ current.document.company_name || '南方电网供应链统一服务平台' }}</span>
              <a v-if="current.document.source_url" :href="current.document.source_url" target="_blank">
                <el-icon><Link /></el-icon>
                官网原文
              </a>
            </div>
          </div>

          <div class="blocks">
            <section v-for="block in current.blocks" :key="block.id" class="doc-block">
              <h4 v-if="block.title">{{ block.section_no ? `${block.section_no} ` : '' }}{{ block.title }}</h4>
              <p v-if="block.text_content">{{ block.text_content }}</p>
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
                <div v-for="(line, lineIndex) in tableLines(block)" :key="lineIndex">{{ line }}</div>
              </div>
            </section>
          </div>
        </article>

        <aside class="summary-panel">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="项目编号">{{ current.document.project_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="项目名称">{{ current.document.project_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="采购人">{{ current.document.buyer || '-' }}</el-descriptions-item>
            <el-descriptions-item label="代理机构">{{ current.document.agency || '-' }}</el-descriptions-item>
            <el-descriptions-item label="公告类型">{{ current.document.announcement_type || '-' }}</el-descriptions-item>
          </el-descriptions>

          <div class="requirements">
            <h3>招标要求</h3>
            <el-collapse>
              <el-collapse-item
                v-for="item in requirementGroups"
                :key="item.id"
                :title="item.requirement_type || item.requirement_title || `要求 ${item.requirement_order}`"
                :name="item.id"
              >
                <p>{{ item.requirement_text || '-' }}</p>
              </el-collapse-item>
            </el-collapse>
          </div>
        </aside>
      </div>
    </section>
  </main>
</template>
