export const VIEW_META = {
  overview: {
    name: "预测总览",
    title: "国家预测总览",
    short: "参数、卡片和图表",
    note: "用仓库里一致的壳层风格来承载国家级预测工作流。",
    icon: "◎"
  },
  model: {
    name: "模型设置",
    title: "模型设置",
    short: "测试、保存、清除",
    note: "将云端模型配置独立出来，靠近 PowerModel 的模型设置页。",
    icon: "◇"
  },
  report: {
    name: "报告问答",
    title: "报告与问答",
    short: "润色与问答",
    note: "把报告和问答放入一个独立业务视图，减少总览页负担。",
    icon: "◌"
  },
  sources: {
    name: "数据来源",
    title: "数据来源",
    short: "字段与来源说明",
    note: "单独展示清洗后数据、原始数据和文档说明。",
    icon: "▣"
  }
};

export const NAV_ITEMS = Object.entries(VIEW_META).map(([key, value]) => ({
  key,
  title: value.name,
  note: value.short,
  icon: value.icon
}));
