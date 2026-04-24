"""
Python → 악! 기합 해병이 되고 싶어! 변환기

지원하는 Python 구문:
  x = <int>              변수 선언 / 재할당
  x = y                  변수 복사
  x = int(input())       정수 입력
  x = a + b / x = a - b  이항 덧셈·뺄셈 (변수 또는 정수 리터럴)
  x += y / x -= y        복합 대입 덧셈·뺄셈 (변수 또는 정수 리터럴)
  print(chr(x))          문자 출력
  if x: / if x != 0:     조건문 (else 미지원)
  while x: / while x!=0: 반복문 (else 미지원)
  arr = []               창고 선언 (최대 5개)
  arr[i] = v             창고 값 할당
  x = arr[i]             창고 값 읽기
  del arr                창고 정리

지원하지 않는 것은 # 변환 불가: ... 로 표시됩니다.

배열 인덱스는 1~256이어야 합니다 (Marine-lang 제약).
"""

import ast
import sys


# ─────────────────────── 정수 변환 ────────────────────────────

def int_to_marine(n: int) -> str:
    """Python int → 해병 정수 표기 (예: 65 → '악!!!!!!!!악!!!!!') """
    if n == 0:
        return '악'
    negative = n < 0
    n = abs(n)
    result = ''.join('악' + '!' * int(d) for d in str(n))
    return ('아' if negative else '') + result


# ─────────────────────── 변환기 ───────────────────────────────

class MarineConverter:
    WAREHOUSE_NAMES = ['종합창고', '피복창고', '물류창고', '부식창고', '치장창고']

    def __init__(self):
        self.var_map: dict[str, str] = {}   # Python 변수명 → Marine 변수명
        self.marine_decl_count = 0           # 신병 받아라 발행 횟수 (인터프리터 var_count와 동기화)
        self.output_lines: list[str] = []
        self.indent_level = 0
        self.supply_ready = False
        self.warehouse_map: dict[str, str] = {}    # Python 리스트명 → 창고명
        self.warehouse_active: set[str] = set()    # 현재 사용 중인 창고들

    # ────────────────────── emit 헬퍼 ─────────────────────────

    def _emit(self, line: str):
        self.output_lines.append('    ' * self.indent_level + line)

    def _unsupported(self, node, reason: str = ''):
        try:
            src = ast.unparse(node)
        except Exception:
            src = repr(node)
        suffix = f' ({reason})' if reason else ''
        self._emit(f'# 변환 불가: {src}{suffix}')

    # ────────────────── 변수 관리 ─────────────────────────────

    def _declare_var(self, python_name: str | None, init_val: int) -> str:
        """
        신병 받아라 <init_val> 를 emit하고 새 Marine 변수를 발급한다.
        python_name이 있으면 var_map에 등록한다.
        """
        self.marine_decl_count += 1
        m = '아쎄이' + '!' * self.marine_decl_count
        if python_name is not None:
            self.var_map[python_name] = m
        self._emit(f'신병 받아라 {int_to_marine(init_val)}')
        return m

    def _marine(self, python_name: str) -> str | None:
        return self.var_map.get(python_name)

    # ────────────────── 값 토큰 해석 ──────────────────────────

    def _token_of(self, node) -> str | None:
        """
        ast 노드를 Marine 언어에서 직접 쓸 수 있는 토큰으로 변환.
        정수 리터럴 → marine int 표기
        변수         → marine 변수명
        변환 불가    → None
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return int_to_marine(node.value)
        if isinstance(node, ast.Name):
            return self._marine(node.id)
        return None

    def _ensure_var_token(self, node) -> str | None:
        """
        돌격/역돌격 RHS는 반드시 변수여야 한다.
        정수 리터럴이면 임시 변수를 선언해 변수 토큰을 반환한다.
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return self._declare_var(None, node.value)
        if isinstance(node, ast.Name):
            return self._marine(node.id)
        return None

    # ────────────────── 보급병 준비 ───────────────────────────

    def _ensure_supply(self):
        if not self.supply_ready:
            # 맨 앞에 삽입
            self.output_lines.insert(0, '보급병! 과업 준비!')
            self.supply_ready = True

    # ─────────────────── 구문 방문 ────────────────────────────

    def visit_body(self, stmts):
        for stmt in stmts:
            self.visit_stmt(stmt)

    def visit_stmt(self, node):
        if isinstance(node, ast.Assign):
            self.visit_assign(node)
        elif isinstance(node, ast.AugAssign):
            self.visit_augassign(node)
        elif isinstance(node, ast.Expr):
            self.visit_expr_stmt(node)
        elif isinstance(node, ast.If):
            self.visit_if(node)
        elif isinstance(node, ast.While):
            self.visit_while(node)
        elif isinstance(node, ast.Delete):
            self.visit_delete(node)
        elif isinstance(node, ast.Pass):
            pass
        else:
            self._unsupported(node)

    # ─────────────── 대입문 ───────────────────────────────────

    def visit_assign(self, node: ast.Assign):
        if len(node.targets) != 1:
            self._unsupported(node, '다중 대입 타겟 미지원')
            return

        target = node.targets[0]

        # arr[i] = v
        if isinstance(target, ast.Subscript):
            self._assign_subscript(target, node.value)
            return

        if not isinstance(target, ast.Name):
            self._unsupported(node, '복잡한 대입 타겟')
            return

        name = target.id

        # x = int(input())
        if self._is_int_input(node.value):
            self._assign_from_input(name)
            return

        # arr = [] 또는 arr = [None]*N
        if self._is_list_init(node.value):
            self._assign_warehouse(name)
            return

        # x = arr[i]
        if isinstance(node.value, ast.Subscript):
            self._assign_from_subscript(name, node.value)
            return

        # x = a + b  /  x = a - b
        if isinstance(node.value, ast.BinOp) and not self._is_list_init(node.value):
            self._assign_from_binop(name, node.value)
            return

        # x = <int literal>
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
            self._assign_int(name, node.value.value)
            return

        # x = y
        if isinstance(node.value, ast.Name):
            self._assign_var(name, node.value.id)
            return

        self._unsupported(node)

    def _is_int_input(self, node) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == 'int'
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Call)
            and isinstance(node.args[0].func, ast.Name)
            and node.args[0].func.id == 'input'
        )

    def _is_list_init(self, node) -> bool:
        if isinstance(node, ast.List) and not node.elts:
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            return isinstance(node.left, ast.List) or isinstance(node.right, ast.List)
        return False

    def _assign_from_input(self, name: str):
        self._emit('헤이빠빠리빠')
        if name not in self.var_map:
            m = self._declare_var(name, 0)
            self._emit(f'{m} 아쎄이 돌격')
        else:
            m = self.var_map[name]
            self._emit(f'{m} {m} 역돌격')
            self._emit(f'{m} 아쎄이 돌격')

    def _assign_warehouse(self, name: str):
        if len(self.warehouse_active) >= len(self.WAREHOUSE_NAMES):
            self._emit('# 변환 불가: 창고가 이미 5개 모두 사용 중입니다')
            return
        if name in self.warehouse_map:
            self._emit(f'# 변환 불가: {name} 은 이미 창고에 연결되어 있습니다')
            return
        self._ensure_supply()
        for wh in self.WAREHOUSE_NAMES:
            if wh not in self.warehouse_active:
                self.warehouse_map[name] = wh
                self.warehouse_active.add(wh)
                self._emit('보급병! 창고로 이동')
                return

    def _assign_subscript(self, target: ast.Subscript, value_node):
        if not isinstance(target.value, ast.Name):
            self._unsupported(target, '복잡한 배열 타겟')
            return
        list_name = target.value.id
        if list_name not in self.warehouse_map:
            self._emit(f'# 변환 불가: {list_name}은 선언된 창고가 아닙니다')
            return
        wh = self.warehouse_map[list_name]
        idx_tok = self._token_of(target.slice)
        val_tok = self._token_of(value_node)
        if idx_tok is None or val_tok is None:
            self._unsupported(target, '인덱스 또는 값 변환 불가')
            return
        self._emit(f'보급병! {wh} 관리하겠습니다 {idx_tok} {val_tok}')

    def _assign_from_subscript(self, dst_name: str, subscript: ast.Subscript):
        if not isinstance(subscript.value, ast.Name):
            self._unsupported(subscript, '복잡한 배열 소스')
            return
        list_name = subscript.value.id
        if list_name not in self.warehouse_map:
            self._emit(f'# 변환 불가: {list_name}은 선언된 창고가 아닙니다')
            return
        wh = self.warehouse_map[list_name]
        idx_tok = self._token_of(subscript.slice)
        if idx_tok is None:
            self._unsupported(subscript, '인덱스 변환 불가')
            return
        if dst_name not in self.var_map:
            m = self._declare_var(dst_name, 0)
        else:
            m = self.var_map[dst_name]
        self._emit(f'{m} {wh} 조사하겠습니다 {idx_tok}')

    def _assign_int(self, name: str, val: int):
        if name not in self.var_map:
            self._declare_var(name, val)
        else:
            m = self.var_map[name]
            self._emit(f'{m} {m} 역돌격')
            if val != 0:
                temp = self._declare_var(None, val)
                self._emit(f'{m} {temp} 돌격')

    def _assign_var(self, dst_name: str, src_name: str):
        src = self._marine(src_name)
        if src is None:
            self._emit(f'# 변환 불가: {src_name} 변수가 선언되지 않았습니다')
            return
        if dst_name not in self.var_map:
            m = self._declare_var(dst_name, 0)
            self._emit(f'{m} {src} 돌격')
        else:
            m = self.var_map[dst_name]
            self._emit(f'{m} {m} 역돌격')
            self._emit(f'{m} {src} 돌격')

    def _assign_from_binop(self, dst_name: str, node: ast.BinOp):
        """x = a + b  /  x = a - b 변환 (덧셈·뺄셈 한 단계만 지원)"""
        if not isinstance(node.op, (ast.Add, ast.Sub)):
            self._unsupported(node, '덧셈/뺄셈만 지원')
            return

        # dst가 우변에 이미 나타나는 경우(자기 참조) → 안전하지 않으므로 불가
        expr_names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        if dst_name in expr_names and dst_name in self.var_map:
            self._unsupported(node, f'{dst_name}이 우변에 있는 경우 += / -= 를 사용하세요')
            return

        # 피연산자를 먼저 변수 토큰으로 확보 (int 리터럴이면 신병 받아라 먼저 emit)
        left_var = self._ensure_var_token(node.left)
        if left_var is None:
            self._unsupported(node, '왼쪽 피연산자 변환 불가')
            return
        right_var = self._ensure_var_token(node.right)
        if right_var is None:
            self._unsupported(node, '오른쪽 피연산자 변환 불가')
            return

        # dst 초기화
        if dst_name not in self.var_map:
            m = self._declare_var(dst_name, 0)
        else:
            m = self.var_map[dst_name]
            self._emit(f'{m} {m} 역돌격')

        # dst += left,  dst op= right
        self._emit(f'{m} {left_var} 돌격')
        if isinstance(node.op, ast.Add):
            self._emit(f'{m} {right_var} 돌격')
        else:
            self._emit(f'{m} {right_var} 역돌격')

    # ─────────────── 복합 대입문 (+=, -=) ─────────────────────

    def visit_augassign(self, node: ast.AugAssign):
        if not isinstance(node.target, ast.Name):
            self._unsupported(node, '변수에 대한 +=/-= 만 지원')
            return
        name = node.target.id
        m = self._marine(name)
        if m is None:
            self._unsupported(node, f'{name} 변수가 선언되지 않았습니다')
            return

        rhs = self._ensure_var_token(node.value)
        if rhs is None:
            self._unsupported(node, 'RHS 변환 불가')
            return

        if isinstance(node.op, ast.Add):
            self._emit(f'{m} {rhs} 돌격')
        elif isinstance(node.op, ast.Sub):
            self._emit(f'{m} {rhs} 역돌격')
        else:
            self._unsupported(node, '덧셈/뺄셈만 지원')

    # ─────────────── 표현식 문 (print 등) ─────────────────────

    def visit_expr_stmt(self, node: ast.Expr):
        expr = node.value
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == 'print':
            self._handle_print(expr)
        else:
            self._unsupported(node)

    def _handle_print(self, call: ast.Call):
        # print(chr(x)) 만 지원 (키워드 인수는 무시)
        if len(call.args) != 1:
            self._unsupported(call, 'print(chr(x)) 형식만 지원')
            return
        arg = call.args[0]
        if not (isinstance(arg, ast.Call)
                and isinstance(arg.func, ast.Name)
                and arg.func.id == 'chr'
                and len(arg.args) == 1):
            self._unsupported(call, 'print(chr(x)) 형식만 지원')
            return

        chr_arg = arg.args[0]
        # 반드시 변수 토큰이어야 함 (돌격은 변수끼리만)
        m = self._ensure_var_token(chr_arg)
        if m is None:
            self._unsupported(call, 'chr 인자 변환 불가')
            return

        self._emit('아쎄이 아쎄이 역돌격')
        self._emit(f'아쎄이 {m} 돌격')
        self._emit('라이라이 차차차')

    # ─────────────── 조건문 / 반복문 ──────────────────────────

    def _condition_var(self, test) -> str | None:
        """
        조건식에서 Marine 변수 추출.
        지원: x  /  x != 0  /  x > 0
        """
        if isinstance(test, ast.Name):
            return self._marine(test.id)
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            left, op, right = test.left, test.ops[0], test.comparators[0]
            if (isinstance(left, ast.Name)
                    and isinstance(right, ast.Constant)
                    and right.value == 0
                    and isinstance(op, (ast.NotEq, ast.Gt))):
                return self._marine(left.id)
        return None

    def visit_if(self, node: ast.If):
        if node.orelse:
            self._unsupported(node, 'else/elif 블록 미지원')
            return
        m = self._condition_var(node.test)
        if m is None:
            self._unsupported(node, '조건은 "변수" / "변수 != 0" / "변수 > 0" 만 지원')
            return
        self._emit(f'{m} 여쭤봐도 되겠습니까 필승')
        self.indent_level += 1
        self.visit_body(node.body)
        self.indent_level -= 1
        self._emit('받아쓰')

    def visit_while(self, node: ast.While):
        if node.orelse:
            self._unsupported(node, 'else 블록 미지원')
            return
        m = self._condition_var(node.test)
        if m is None:
            self._unsupported(node, '조건은 "변수" / "변수 != 0" / "변수 > 0" 만 지원')
            return
        self._emit(f'{m} 다시 알아보겠습니다 필승')
        self.indent_level += 1
        self.visit_body(node.body)
        self.indent_level -= 1
        self._emit('받아쓰')

    # ─────────────── del ──────────────────────────────────────

    def visit_delete(self, node: ast.Delete):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in self.warehouse_map:
                wh = self.warehouse_map.pop(target.id)
                self.warehouse_active.discard(wh)
                self._emit(f'보급병! {wh} 정리하겠습니다')
            else:
                self._unsupported(node)

    # ─────────────── 진입점 ───────────────────────────────────

    def convert(self, source: str) -> str:
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return f'# Python 구문 오류: {e}'
        self.visit_body(tree.body)
        return '\n'.join(self.output_lines)


# ─────────────────────── main ─────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print('사용법: python convert_py_to_ak.py <파이썬파일.py>')
        sys.exit(1)
    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f'파일을 찾을 수 없습니다: {sys.argv[1]}')
        sys.exit(1)

    result = MarineConverter().convert(source)
    print(result)


if __name__ == '__main__':
    main()
