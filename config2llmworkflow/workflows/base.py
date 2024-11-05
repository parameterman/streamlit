import re
from typing import List, Dict, Any
import concurrent.futures
import streamlit as st
from config2llmworkflow.configs.workflows.base import BaseWorkflowConfig
from config2llmworkflow.nodes.base import Node
from config2llmworkflow.configs.nodes.base import NodeType
from loguru import logger


def run_node(node: Node, variables: Dict[str, Any]) -> Dict[str, Any]:
    logger.debug("🔄[Node]Running node: {}", node.config.name)
    logger.debug("🔄[Node]variables: {}", variables)
    return node(variables)


class BaseWorkflow(Node):
    type = NodeType.WORKFLOW

    def __init__(self, config: BaseWorkflowConfig = None):
        super().__init__(config)
        self.config = config
        self.variables = {}
        self.nodes = []

        logger.debug(
            r"🏗️[Workflow]BaseWorkflow -> {}: {}", type(self.config), self.config
        )

        self._init_nodes()

    def _init_nodes(self) -> List[Node]:
        logger.debug("📋[Workflow]self.config.nodes: \n {}", self.config.nodes)

        from config2llmworkflow.utils.factory import NodeFactory

        # 根据类型来创建节点
        for node_config in self.config.nodes:
            logger.info(
                "🔨[Workflow]Creating node: {} \n config: {}",
                node_config.name,
                node_config,
            )
            node = NodeFactory.create(node_config.to_dict())
            self.nodes.append(node)

        logger.info(
            "✅[Workflow]Created nodes for {}: {}",
            self.config.name,
            [node.config.name for node in self.nodes],
        )
        return self.nodes

    @property
    def logs(self) -> Dict[str, Any]:
        logger.debug("📊[Workflow]Current workflow: {}", self.config.name)
        logger.debug(
            "📊[Workflow]Current nodes: {}", [node.config.name for node in self.nodes]
        )

        if self.nodes:
            self.node_log["nodes"] = [node.logs for node in self.nodes]

        return self.node_log


class DefaultWorkflow(BaseWorkflow):

    def __init__(self, config: BaseWorkflowConfig = None):
        super().__init__(config)

    def run(self, input_vars: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("▶️[Workflow]Running default workflow: {}\n", self.config.name)
        logger.debug("📋[Workflow]All nodes: {}\n", self.nodes)
        # 验证输入变量
        for var in self.config.input_vars:
            if var.name not in input_vars:
                raise ValueError(f"Missing input variable: {var.name}")

        # 合并输入变量和已有变量
        self.variables.update(input_vars)
        
        #在此处增加一个智能体用于读取输入，并计算出原始数值更新self.variables

        # 对智能体进行优先级排序
        node_priority_dict = {}
        for node in self.nodes:
            if node.config.priority not in node_priority_dict:
                node_priority_dict[node.config.priority] = []
            node_priority_dict[node.config.priority].append(node)
        logger.info("🔀[Workflow]node_priority_dict: {}\n", node_priority_dict)

        # 获取所有优先级，从 1 到 n 排序
        priorities = sorted(node_priority_dict.keys())

        
        # 逐个优先级运行智能体, 必须按照优先级顺序运行
        output_vars = {}
        for priority in priorities:
            logger.info("⚡[Workflow]Running nodes at priority {}\n", priority)
            nodes = node_priority_dict[priority]

            # 多线程并行运行智能体
            # run_node 返回 Dict[str, Any]
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(run_node, node, self.variables) for node in nodes
                ]
                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            # 更新变量
            for result in results:
                
                self.variables.update(result)
            
            # 更新输出变量
            import json,re
            datas = {}
            for node in nodes:
                for var in node.config.output_vars:
                    output_vars[var.name] = self.variables[var.name]
                    if var.name == 'summary_1':
                        logger.info("⚡ summary_1:{}\n",self.variables['summary_1'])
                        pattern = r'[\'\"]*(\w+)["]*:\s*["]*([-+]?\d+\.?\d*)[\'\"]*'
                        matches = re.findall(pattern, self.variables['summary_1'])
                        # result_1 = json.loads(matches)
                        # for match in matches:
                        result_1 = {key: value for key, value in matches}
                        if result_1:
                        # result_1=json.loads(self.variables['summary_1'])
                            logger.info("⚡ summary_1:{}\n",result_1)
                            output_vars.update(result_1)
                        else:
                            
                            st.write("Agent1 识别有误，请再次运行")
                            # raise ValueError("result_1 is None, rerun please.")
                        
                    if var.name == 'summary_2':
                        logger.info("⚡ summary_2:{}\n",self.variables['summary_2'])
                        pattern = r'[\'\"]*(\w+)[\'\"]*:\s*[\'\"]*([-+]?\d+\.?\d*)[\'\"]*'
                        matches = re.findall(pattern, self.variables['summary_2'])
                        # result_1 = json.loads(matches)
                        # for match in matches:
                        data = {key: value for key, value in matches}
                        
                        output_vars.update(data)
                        L1 = 2*float(data['dL1'])+float(data['hL1'])+0.8*float(data['tL1'])
                        U1 = 2*float(data['dU1'])+float(data['hU1'])+0.8*float(data['tU1'])
                        output_vars.update({'L1':L1,'U1':U1})
                        self.variables['summary_2'] += "{下切牙所需的牙列间隙变化L1:"+str(L1)+",'上切牙所需的牙列间隙变化U1': '"+str(U1)+"' }"
                        logger.info("⚡ summary_2:{}\n",output_vars)
                        # logger.info("⚡ summary_2:{}\n",data)

                    if var.name == 'summary_3':
                        logger.info("⚡ summary_3:{}\n",self.variables['summary_3'])
                        # pattern = r'"(\w+)":\s*(\S+)'
                        # matches = re.findall(pattern, self.variables['summary_3'])
                        pattern = r'[\'\"]*(\w+)[\'\"]*:\s*[\'\"]*([-+]?\d+\.?\d*)[\'\"]*'
                        matches = re.findall(pattern, self.variables['summary_3'])
                        # result_1 = json.loads(matches)
                        # for match in matches:
                        data = {key: value for key, value in matches}
                        if data:
                        # result_1=json.loads(self.variables['summary_1'])
                            # logger.info("⚡ _1:{}\n",result_1)
                            output_vars.update(data)
                        else:
                            # import streamlit as st
                            st.write("Agent3 识别有误，请再次运行")
                        
                        # 计算上下总间隙量
                        kuoGong = float(data['D1'])+4-float(data['D2'])
                        logger.info("⚡扩弓量=D1{}-D2{}+4 ：{}\n",data['D1'],data['D2'],kuoGong)
                        shangHe = ((float(data['上颌左侧第一磨牙颊面转矩'])+float(data['上颌右侧第一磨牙颊面转矩'])) + 18)*0.2
                        logger.info("⚡上颌平均：{}\n",shangHe)
                        xiaHe = ((float(data['下颌左侧第一磨牙颊面转矩'])+float(data['下颌右侧第一磨牙颊面转矩'])) + 60)*0.2
                        logger.info("⚡下颌平均：{}\n",xiaHe)
                        
                        output_vars.update({'上颌总间隙量':kuoGong+shangHe,'下颌总间隙量':kuoGong+xiaHe})
                        logger.info("⚡ summary_3:{}\n",output_vars)
                        self.variables['summary_3'] += "{'上颌总间隙量':"+str(kuoGong+shangHe)+",'下颌总间隙量': '"+str(kuoGong+xiaHe)+"' }"
                    if var.name == 'summary_4':
                        logger.info("⚡ summary_4:{}\n",self.variables['summary_4'])
                        pattern = r'[\'\"]*(\w+)[\'\"]*:\s*[\'\"]*([-+]?\d+\.?\d*)[\'\"]*'
                        matches = re.findall(pattern, self.variables['summary_4'])
                        # result_1 = json.loads(matches)
                        # for match in matches:
                        data = {key: value for key, value in matches}
                        if data:
                        # result_1=json.loads(self.variables['summary_1'])
                            # logger.info("⚡ _1:{}\n",result_1)
                            output_vars.update(data)
                        else:
                            # import streamlit as st
                            st.write("Agent4识别有误，请再次运行")
                        SpeeAvg = 0.5*(float(data['左Spee曲线深度']) + float(data['右Spee曲线深度']))
                        # output_vars.update(data)
                        output_vars.update({'Spee曲整平所需间隙':SpeeAvg+0.5})
                        logger.info("⚡ Agent 4 data:{}\n",output_vars)
                    if var.name == 'summary_5':
                        logger.info("⚡ summary_5:{}\n",self.variables['summary_5'])
                        pattern = r'[\'\"]*(\w+)[\'\"]*:\s*[\'\"]*([-+]?\d+\.?\d*)[\'\"]*'
                        matches = re.findall(pattern, self.variables['summary_5'])
                        data = {key: value for key, value in matches}
                        if data:
                        # result_1=json.loads(self.variables['summary_1'])
                            # logger.info("⚡ _1:{}\n",result_1)
                            output_vars.update(data)
                        else:
                            # import streamlit as st
                            st.write("Agent5 识别有误，请再次运行")
                        # output_vars.update(data)
                        logger.info("⚡ summary_5:{}\n",data)
                 
                    if var.name == 'summary_6':
                        logger.info("⚡ result_6:{}\n",output_vars['result_6'])
                        pattern = r'[\'\"]*(\w+)[\'\"]*:\s*[\'\"]*([-+]?\d+\.?\d*)[\'\"]*'
                        matches = re.findall(pattern, self.variables['result_6'])
                        data = {key: value for key, value in matches}
                        if data:
                        # result_1=json.loads(self.variables['summary_1'])
                            # logger.info("⚡ _1:{}\n",result_1)
                            output_vars.update(data)
                        else:
                            # import streamlit as st
                            st.write("Agent6 识别有误，请再次运行")
                        shangHeZong = float(data['A1']) + float(data['B1']) +float(data['C1']) + float(data['D1'])
                        xiaHeZong = float(data['A2']) + float(data['B2']) +float(data['C2']) + float(data['D2']) +float(data['E2']) 
                        logger.info("⚡ result_6:{}\n",data)
                        result = {'上颌总间隙需求量':shangHeZong,'下颌总间隙需求量':xiaHeZong}
                        self.variables.update({'summary_6':result})


        logger.info(
            "✅[Workflow]Finished running default workflow: {}", self.config.name
        )
        return output_vars

    def to_dict(self):
        return {
            "config": self.config.model_dump(),
            "nodes": [node.to_dict() for node in self.nodes],
        }
