from reflection.memory import Memory
from original_agent.build_first_agent import HelloAgentsLLM
from reflection.init_prompt import INIT_PROMPT_TEMPLATE
from reflection.refinement_prompt import REFINE_PROMPT_TEMPLATE
from reflection.reflection_prompt import REFLECTION_PROMPT_TEMPLATE

class ReflectionAgent:
    
    def __init__(self,llm_client : HelloAgentsLLM,max_iterations=3) -> None:
        self.llm_client = llm_client
        self.memory = Memory()
        self.max_iterations = max_iterations
        
    
    def run(self,task: str):
        print(f"\n ---- 开始处理任务 ----\n任务：{task}")

        # --- 1.初始执行 ---
        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = INIT_PROMPT_TEMPLATE.format(task=task)
        initial_code = self._get_llm_response(initial_prompt)
        self.memory.add_record("execution",initial_code)

        # --- 2.迭代循环：反思与优化 ---
        for i in range(self.max_iterations):
            print(f"\n --- 第{i+1}/{self.max_iterations} 轮迭代 ---")

            # a. 反思
            print("\n-> 正在进行反思...")
            last_code = self.memory.get_last_execution()
            reflect_prompt = REFLECTION_PROMPT_TEMPLATE.format(task=task,code=last_code)
            feedback = self._get_llm_response(reflect_prompt)
            print(f"\n-> 反思反馈:\n {feedback}\n")
            self.memory.add_record("reflection",feedback)

            # b.检查是否需要停止
            if "无需改进" in feedback:
                print("\n✅ 反思认为代码已无需改进，任务完成。")
                break

            # c.优化
            print("\n-> 正在进行优化...")
            refine_prompt = REFINE_PROMPT_TEMPLATE.format(
                task = task,
                last_code_attempt = last_code,
                feedback = feedback
            )

            refined_code = self._get_llm_response(refine_prompt)
            self.memory.add_record("execution",refined_code)
        
        final_code = self.memory.get_last_execution()
        print(f"\n --- 任务完成 ---\n 最终生成的代码:\n {final_code}\n")
        return final_code


    def _get_llm_response(self,prompt :str) -> str:
        """一个辅助方法，用于调用LLM"""
        messages = [{"role":"user","content":prompt}]
        response_text = self.llm_client.think(messages = messages) or ""
        return response_text


if __name__ == '__main__':
    # 1. 初始化LLM客户端 (请确保你的 .env 和 llm_client.py 文件配置正确)
    try:
        llm_client = HelloAgentsLLM()
    except Exception as e:
        print(f"初始化LLM客户端时出错: {e}")
        exit()

    # 2. 初始化 Reflection 智能体，设置最多迭代2轮
    agent = ReflectionAgent(llm_client, max_iterations=2)

    # 3. 定义任务并运行智能体
    task = "编写一个Python函数，找出1到n之间所有的素数 (prime numbers)。"
    agent.run(task)

# 这个运行实例展示出 Reflection 机制是如何驱动智能体进行深度优化的
# - 有效的"批判"是优化的前提：第一轮反思中，由于我们使用"极其严格"且"专注于算法效率"的提示词，智能体没有满足于功能正确的初版代码，而是精准地指出了其时间复杂度瓶颈，并提出算法层面的优化建议
# - 迭代式改进：智能体在接收到明确的反馈后，于优化阶段成功地实现了更高效的筛选，将算法复杂度降至 O(n log log n)，完成了第一次有意义的自我迭代
# - 收敛于终止：第二次反思中，智能体面对已经高效的筛选，展示出更深层次的知识。它不仅肯定了当前算法的效率，甚至还提及了分段筛法等更高级的优化方向，但最终做出来"在一般情况下无需改进"的正确判断

#  ---- 开始处理任务 ----
# 任务：编写一个Python函数，找出1到n之间所有的素数 (prime numbers)。

# --- 正在进行初始尝试 ---
# 🧠 正在调用 mimo-v2.5-pro 模型...
# ✅ 大语言模型响应成功:
# ```python
# def find_primes(n: int) -> list[int]:
#     """
#     Find all prime numbers between 1 and n using the Sieve of Eratosthenes.

#     Args:
#         n (int): The upper limit (inclusive) to search for primes.
#                  Must be a positive integer.

#     Returns:
#         list[int]: A list of all prime numbers from 2 to n.
#                    Returns an empty list if n < 2.

#     Raises:
#         ValueError: If n is not a positive integer.

#     Examples:
#         >>> find_primes(10)
#         [2, 3, 5, 7]
#         >>> find_primes(20)
#         [2, 3, 5, 7, 11, 13, 17, 19]
#         >>> find_primes(1)
#         []
#     """
#     if not isinstance(n, int) or n <= 0:
#         raise ValueError("n must be a positive integer")

#     if n < 2:
#         return []

#     # Initialize a boolean list where index represents the number
#     is_prime = [True] * (n + 1)
#     is_prime[0] = is_prime[1] = False  # 0 and 1 are not prime

#     # Sieve of Eratosthenes algorithm
#     for i in range(2, int(n**0.5) + 1):
#         if is_prime[i]:
#             # Mark all multiples of i as non-prime
#             for j in range(i * i, n + 1, i):
#                 is_prime[j] = False
    
#     # Collect all prime numbers
#     primes = [i for i in range(2, n + 1) if is_prime[i]]
#     return primes
# ```
# 📝 记忆已更新，新增一条 'execution' 记录。

#  --- 第1/2 轮迭代 ---

# -> 正在进行反思...
# 🧠 正在调用 mimo-v2.5-pro 模型...
# ✅ 大语言模型响应成功:
# 当前代码使用埃拉托斯特尼筛法，时间复杂度为 O(n log log n)，空间复杂度为 O(n)。算法效率的主要瓶颈是每个合数可能被多个质数重复标记，导致冗余操作。

# 存在算法上更优的解决方案：使用线性筛（欧拉筛）算法，时间复杂度 O(n)，每个合数只被标记一次，显著提升性能。建议实现线性筛替代当前算法。
# 📝 记忆已更新，新增一条 'reflection' 记录。

# -> 正在进行优化...
# 🧠 正在调用 mimo-v2.5-pro 模型...
# ✅ 大语言模型响应成功:
# ```python
# def find_primes(n: int) -> list[int]:
#     """
#     Find all prime numbers between 1 and n using the linear sieve (Euler's sieve).

#     Args:
#         n (int): The upper limit (inclusive) to search for primes.
#                  Must be a positive integer.

#     Returns:
#         list[int]: A list of all prime numbers from 2 to n.
#                    Returns an empty list if n < 2.

#     Raises:
#         ValueError: If n is not a positive integer.

#     Examples:
#         >>> find_primes(10)
#         [2, 3, 5, 7]
#         >>> find_primes(20)
#         [2, 3, 5, 7, 11, 13, 17, 19]
#         >>> find_primes(1)
#         []
#     """
#     if not isinstance(n, int) or n <= 0:
#         raise ValueError("n must be a positive integer")

#     if n < 2:
#         return []

#     # Initialize a boolean list where index represents the number
#     is_prime = [True] * (n + 1)
#     primes = []  # List to store discovered primes

#     # Linear sieve algorithm (Euler's sieve)
#     for i in range(2, n + 1):
#         if is_prime[i]:
#             primes.append(i)  # i is prime, add to list

#         # Mark multiples of primes as composite
#         for p in primes:
#             if i * p > n:
#                 break
#             is_prime[i * p] = False
#             if i % p == 0:  # p is the smallest prime factor of i
#                 break

#     return primes
# ```
# 📝 记忆已更新，新增一条 'execution' 记录。

#  --- 第2/2 轮迭代 ---

# -> 正在进行反思...
# 🧠 正在调用 mimo-v2.5-pro 模型...
# ✅ 大语言模型响应成功:
# 当前代码使用了线性筛法（Euler’s sieve），其时间复杂度为 O(n)，空间复杂度为 O(n)。该算法在理论上是寻找所有小于等于 n 的素数的最优算法之一，因为它能确保每个合数只被其最小质因子筛去一次。

# **结论：该代码在算法层面已达到最优，无需改进。**
# 📝 记忆已更新，新增一条 'reflection' 记录。

# ✅ 反思认为代码已无需改进，任务完成。

#  --- 任务完成 ---
#  最终生成的代码:
#  ```python
# def find_primes(n: int) -> list[int]:
#     """
#     Find all prime numbers between 1 and n using the linear sieve (Euler's sieve).

#     Args:
#         n (int): The upper limit (inclusive) to search for primes.
#                  Must be a positive integer.

#     Returns:
#         list[int]: A list of all prime numbers from 2 to n.
#                    Returns an empty list if n < 2.

#     Raises:
#         ValueError: If n is not a positive integer.

#     Examples:
#         >>> find_primes(10)
#         [2, 3, 5, 7]
#         >>> find_primes(20)
#         [2, 3, 5, 7, 11, 13, 17, 19]
#         >>> find_primes(1)
#         []
#     """
#     if not isinstance(n, int) or n <= 0:
#         raise ValueError("n must be a positive integer")

#     if n < 2:
#         return []

#     # Initialize a boolean list where index represents the number
#     is_prime = [True] * (n + 1)
#     primes = []  # List to store discovered primes

#     # Linear sieve algorithm (Euler's sieve)
#     for i in range(2, n + 1):
#         if is_prime[i]:
#             primes.append(i)  # i is prime, add to list

#         # Mark multiples of primes as composite
#         for p in primes:
#             if i * p > n:
#                 break
#             is_prime[i * p] = False
#             if i % p == 0:  # p is the smallest prime factor of i
#                 break

#     return primes
# ```