export type IpSectionKey = 'ip' | 'strategy' | 'columns' | 'topics'

export interface IpAssetFormShape {
  name: string
  type: string
  industry: string
  targetAudience: string
  businessGoal: string
  mainPlatforms: string
  secondaryPlatforms: string
  tone: string
  visualStyle: string
  conversionPath: string
  forbiddenExpressions: string
}

export interface IpSectionTemplate {
  key: string
  label: string
  description: string
  fields: Partial<IpAssetFormShape>
}

export const ipFieldHints: Record<keyof IpAssetFormShape, { placeholder: string; hint: string }> = {
  name: {
    placeholder: '例如：职场成长说 / 一人公司实验室',
    hint: '对外展示的名称，可以是个人名、栏目名或品牌简称。',
  },
  type: {
    placeholder: '例如：职场IP / 创业者IP / 知识IP',
    hint: '说明这是职场分享、创业记录还是方法论输出账号。',
  },
  businessGoal: {
    placeholder: '例如：建立专业影响力并承接咨询或课程',
    hint: '这个 IP 最终要达成什么业务结果：涨粉、咨询、课程、合作或品牌曝光。',
  },
  industry: {
    placeholder: '例如：职场成长 / 个人创业 / 行业洞察',
    hint: '你主要服务的领域，影响后续选题和话术风格。',
  },
  targetAudience: {
    placeholder: '例如：25-35 岁一线城市白领，关注晋升与跳槽决策',
    hint: '尽量写清年龄、职业阶段、城市层级和核心痛点。',
  },
  mainPlatforms: {
    placeholder: 'wechat,shipinhao',
    hint: '主阵地平台，英文逗号分隔。常用：wechat、shipinhao、xiaohongshu、douyin、moments。',
  },
  secondaryPlatforms: {
    placeholder: 'xiaohongshu,douyin',
    hint: '辅助分发平台，用于引流、种草或二次触达。',
  },
  tone: {
    placeholder: '例如：理性、实战、有洞见，不说空话',
    hint: '内容说话的语气，会约束 AI 生成口播和文章。',
  },
  visualStyle: {
    placeholder: '例如：简洁专业、实拍工作场景、图文清晰',
    hint: '封面、配图和排版倾向，便于后续统一视觉。',
  },
  conversionPath: {
    placeholder: '干货内容 → 收藏关注 → 私信领资料 → 咨询转化',
    hint: '用户从看到内容到完成转化的关键步骤。',
  },
  forbiddenExpressions: {
    placeholder: '绝对化成功承诺、夸大收益、未经证实的捷径',
    hint: '生成内容时必须避开的表达，降低合规和信任风险。',
  },
}

export const ipSectionLabels: Record<IpSectionKey, string> = {
  ip: 'IP 资料',
  strategy: '人设定位',
  columns: '平台配置',
  topics: '内容规则',
}

export const ipSectionTemplates: Record<IpSectionKey, IpSectionTemplate[]> = {
  ip: [
    {
      key: 'workplace_career',
      label: '典型职场 IP',
      description: '适合 HR、管理者、职场教练做晋升、跳槽、管理方法论内容。',
      fields: {
        name: '职场成长说',
        type: '职场IP',
        businessGoal: '帮助职场人突破瓶颈，建立专业影响力并承接咨询或课程',
      },
    },
    {
      key: 'solo_entrepreneur',
      label: '个人创业 IP',
      description: '适合超级个体、小团队创始人在公域记录创业与变现过程。',
      fields: {
        name: '一人公司实验室',
        type: '创业者IP',
        businessGoal: '分享创业实战经验，吸引同频伙伴与高意向合作或客户',
      },
    },
    {
      key: 'knowledge_creator',
      label: '知识博主',
      description: '适合跨行业的方法论、经验复盘型内容创作者。',
      fields: {
        name: '行业经验分享官',
        type: '知识IP',
        businessGoal: '沉淀可复制的方法论，获取高意向私域线索',
      },
    },
  ],
  strategy: [
    {
      key: 'workplace_career',
      label: '职场进阶人群',
      description: '面向有晋升、跳槽、管理转型需求的白领。',
      fields: {
        industry: '职场成长 / 企业管理',
        targetAudience: '25-38 岁一二线城市白领，面临晋升、跳槽、向上管理或团队管理转型焦虑',
      },
    },
    {
      key: 'solo_entrepreneur',
      label: '个人创业人群',
      description: '面向想副业转型或已有小团队的创业者。',
      fields: {
        industry: '个人创业 / 超级个体',
        targetAudience: '28-45 岁想副业转型或已有小团队的创业者，缺方法、缺资源、缺稳定变现路径',
      },
    },
    {
      key: 'knowledge_creator',
      label: '学习型人群',
      description: '面向需要框架、案例和可执行建议的泛知识受众。',
      fields: {
        industry: '职业成长 / 行业洞察',
        targetAudience: '22-35 岁职场人，信息过载，需要可执行的判断标准和真实案例',
      },
    },
  ],
  columns: [
    {
      key: 'workplace_channels',
      label: '职场深度 + 短视频',
      description: '公众号/视频号沉淀方法论，小红书做搜索触达。',
      fields: {
        mainPlatforms: 'wechat,shipinhao',
        secondaryPlatforms: 'xiaohongshu,moments',
      },
    },
    {
      key: 'founder_channels',
      label: '创业公域 + 私域',
      description: '抖音/视频号做曝光，微信承接深度沟通。',
      fields: {
        mainPlatforms: 'douyin,shipinhao',
        secondaryPlatforms: 'wechat,xiaohongshu',
      },
    },
    {
      key: 'omni_channel',
      label: '全渠道分发',
      description: '公域获客 + 私域承接组合，适合多平台同步测试。',
      fields: {
        mainPlatforms: 'wechat,shipinhao,xiaohongshu',
        secondaryPlatforms: 'douyin,moments',
      },
    },
  ],
  topics: [
    {
      key: 'workplace_career',
      label: '职场实战风',
      description: '理性、有洞见，强调可落地的职场建议。',
      fields: {
        tone: '理性、实战、有洞见，不说空话，不贩卖焦虑',
        visualStyle: '简洁专业、图文清晰、少量信息图',
        conversionPath: '干货内容 → 收藏关注 → 私信领资料 → 咨询或课程转化',
        forbiddenExpressions: '绝对化成功承诺、贬低同行、未经证实的职场捷径、保证晋升',
      },
    },
    {
      key: 'solo_entrepreneur',
      label: '创业真实风',
      description: '敢讲过程与失败，强调真实创业颗粒度。',
      fields: {
        tone: '真实、直接、有颗粒度，敢讲失败也讲方法',
        visualStyle: '实拍、白板、工作场景、轻纪录片感',
        conversionPath: '案例复盘 → 评论区交流 → 私信诊断 → 陪跑或合作转化',
        forbiddenExpressions: '稳赚不赔、一夜暴富、夸大收入截图、保证回本',
      },
    },
    {
      key: 'professional_warm',
      label: '专业亲和风',
      description: '专业可信，但保持温度和可读性。',
      fields: {
        tone: '专业、亲和、有温度，避免说教和堆术语',
        visualStyle: '清爽、干净、真实感',
        conversionPath: '内容建立认知 → 评论区互动 → 私信咨询 → 深度服务',
        forbiddenExpressions: '绝对化承诺、未经证实的案例、收益保证、过度焦虑话术',
      },
    },
  ],
}

export const fullExampleIpForm: IpAssetFormShape = {
  name: '职场成长说',
  type: '职场IP',
  industry: '职场成长 / 企业管理',
  targetAudience: '25-38 岁一二线城市白领，面临晋升、跳槽或管理转型焦虑',
  businessGoal: '帮助职场人突破瓶颈，建立专业影响力并承接咨询',
  mainPlatforms: 'wechat,shipinhao',
  secondaryPlatforms: 'xiaohongshu,moments',
  tone: '理性、实战、有洞见，不说空话',
  visualStyle: '简洁专业、图文清晰',
  conversionPath: '干货内容 → 收藏关注 → 私信领资料 → 咨询转化',
  forbiddenExpressions: '绝对化成功承诺、未经证实的捷径、保证晋升',
}

export const ipSectionFields: Record<IpSectionKey, Array<keyof IpAssetFormShape>> = {
  ip: ['name', 'type', 'businessGoal'],
  strategy: ['industry', 'targetAudience'],
  columns: ['mainPlatforms', 'secondaryPlatforms'],
  topics: ['tone', 'visualStyle', 'conversionPath', 'forbiddenExpressions'],
}

export const platformOptions = [
  { key: 'wechat', label: '公众号' },
  { key: 'shipinhao', label: '视频号' },
  { key: 'xiaohongshu', label: '小红书' },
  { key: 'douyin', label: '抖音' },
  { key: 'moments', label: '朋友圈' },
] as const

export function togglePlatformCsv(current: string, platformKey: string) {
  const items = current.split(',').map((item) => item.trim()).filter(Boolean)
  const index = items.indexOf(platformKey)
  if (index >= 0) {
    items.splice(index, 1)
  } else {
    items.push(platformKey)
  }
  return items.join(',')
}
