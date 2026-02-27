import sys

class MarineError(Exception):
    """해병 언어 실행 중 발생하는 오도기합짜세 에러"""
    pass

class MarineLangInterpreter:
    def __init__(self, code: str):
        self.code = code
        self.tokens = []
        self.line_indents = {}  # 줄 번호별 들여쓰기 수준 저장
        self._tokenize()
        self.variables = {'아쎄이': 0}
        self.var_count = 0
        self.jumps = {}
        self._precompute_jumps()

    def _tokenize(self):
        """코드를 토큰으로 분리하고 각 줄의 들여쓰기를 기록한다!"""
        for line_num, line in enumerate(self.code.splitlines(), start=1):
            if not line.strip():
                continue
            # 들여쓰기 계산 (왼쪽 공백 개수)
            indent = len(line) - len(line.lstrip())
            self.line_indents[line_num] = indent
            
            for word in line.split():
                self.tokens.append((word, line_num))

    def _precompute_jumps(self):
        """조건문과 반복문의 블록 위치, 들여쓰기, 필수 키워드 누락을 빡세게 검사한다!"""
        stack = []
        for i, (token, line_num) in enumerate(self.tokens):
            
            # 1. '여쭤봐도 되겠습니까' 뒤에 '필승'이 오는지 검사!
            if token == '여쭤봐도':
                if i + 1 < len(self.tokens) and self.tokens[i+1][0] == '되겠습니까':
                    if i + 2 >= len(self.tokens) or self.tokens[i+2][0] != '필승':
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '여쭤봐도 되겠습니까' 뒤에는 반드시 '필승'이 와야 한다! 기열!")
            
            # 2. '다시 알아보겠습니다' 뒤에 '필승'이 오는지 검사!
            elif token == '다시':
                if i + 1 < len(self.tokens) and self.tokens[i+1][0] == '알아보겠습니다':
                    if i + 2 >= len(self.tokens) or self.tokens[i+2][0] != '필승':
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '다시 알아보겠습니다' 뒤에는 반드시 '필승'이 와야 한다! 기열!")
            
            # 3. 블록 시작점(필승) 스택에 푸시
            elif token == '필승':
                if i >= 2 and self.tokens[i-2][0] == '여쭤봐도':
                    stack.append(('IF', i, line_num, self.line_indents[line_num]))
                elif i >= 2 and self.tokens[i-2][0] == '다시':
                    stack.append(('WHILE', i, line_num, self.line_indents[line_num]))
                else:
                    raise MarineError(f"[줄 {line_num}] 구문 오류: '필승' 앞에는 '여쭤봐도 되겠습니까' 또는 '다시 알아보겠습니다'가 와야 한다! 악!")
            
            # 4. 블록 종료점(받아쓰) 처리
            elif token == '받아쓰':
                if not stack:
                    raise MarineError(f"[줄 {line_num}] 구문 오류: '받아쓰'에 대응하는 '필승'이 없다! 기열!")
                block_type, start_idx, start_line, start_indent = stack.pop()
                self.jumps[start_idx] = i
                self.jumps[i] = start_idx
            
            # 5. 블록 내부 들여쓰기 검사
            else:
                if stack:
                    block_type, start_idx, start_line, start_indent = stack[-1]
                    is_first_token_of_line = (i == 0) or (self.tokens[i-1][1] != line_num)
                    if is_first_token_of_line and line_num > start_line:
                        if self.line_indents.get(line_num, 0) <= start_indent:
                            raise MarineError(f"[줄 {line_num}] 구문 오류: '필승'과 '받아쓰' 사이의 명령문은 반드시 들여쓰기가 되어야 한다! 악!")
        
        # 6. 다 끝났는데 스택에 뭐가 남아있다면 받아쓰가 없는 거다!
        if stack:
            block_type, start_idx, start_line, start_indent = stack.pop()
            raise MarineError(f"[줄 {start_line}] 구문 오류: '필승'에 대응하는 '받아쓰'가 닫히지 않았다! 탈영인가!")

    def _parse_number(self, s: str, line_num: int) -> int:
        """해병 정수를 엄격하게 파싱한다!"""
        if not s:
            raise MarineError(f"[줄 {line_num}] 구문 오류: 숫자가 비어있다!")
            
        for char in s:
            if char not in ['악', '!', '아']:
                raise MarineError(f"[줄 {line_num}] 구문 오류: 정수 표기에 '악', '!', '아' 외의 흘러빠진 문자가 포함되어 있다!")
                
        is_negative = s.startswith('아')
        check_s = s[1:] if is_negative else s
        
        if '아' in check_s:
            raise MarineError(f"[줄 {line_num}] 구문 오류: '아'는 음수 표기를 위해 맨 앞에만 올 수 있다! 기열!")
            
        if not check_s.startswith('악'):
            raise MarineError(f"[줄 {line_num}] 구문 오류: 정수는 무조건 '악'으로 시작해야 한다!")
            
        parts = check_s.split('악')[1:]
        digits = []
        for p in parts:
            if len(p) >= 10:
                raise MarineError(f"[줄 {line_num}] 구문 오류: '악' 뒤에 '!'가 10개 이상 붙을 수 없다!")
            digits.append(str(len(p)))
            
        if not digits:
            return 0
            
        try:
            val = int("".join(digits))
            return -val if is_negative else val
        except ValueError:
            raise MarineError(f"[줄 {line_num}] 구문 오류: 올바르지 않은 해병 정수 형식이다!")

    def _check_variable(self, var_name: str, line_num: int):
        """변수가 제대로 입대(선언)했는지 확인한다!"""
        if var_name not in self.variables:
            raise MarineError(f"[줄 {line_num}] 런타임 오류: 선언되지 않은 변수를 사용했다! 미확인 인원 접근!")

    def run(self):
        """인터프리터 실행 (돌격!)"""
        pc = 0
        while pc < len(self.tokens):
            token, line_num = self.tokens[pc]
            
            try:
                # 1. 변수 선언: 신병 받아라 (정수)
                if token == '신병' and pc + 1 < len(self.tokens) and self.tokens[pc+1][0] == '받아라':
                    if pc + 2 >= len(self.tokens):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '신병 받아라' 뒤에 정수가 오지 않았다!")
                    
                    val_token = self.tokens[pc+2][0]
                    # 정수 형태인지 1차 검사
                    if not any(c in val_token for c in ['악', '!', '아']):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '신병 받아라' 뒤에 올바른 해병 정수가 오지 않았다!")
                        
                    val = self._parse_number(val_token, line_num)
                    self.var_count += 1
                    var_name = '아쎄이' + ('!' * self.var_count)
                    self.variables[var_name] = val
                    pc += 3
                    continue
                    
                # 2. 입력: 헤이빠빠리빠
                if token == '헤이빠빠리빠':
                    user_input = sys.stdin.readline().strip()
                    try:
                        self.variables['아쎄이'] = int(user_input)
                    except ValueError:
                        raise MarineError(f"[줄 {line_num}] 런타임 오류: '헤이빠빠리빠' 입력 시 해병 정수 외의 기열 값이 들어왔다!")
                    pc += 1
                    continue
                    
                # 3. 출력: 라이라이 차차차
                if token == '라이라이' and pc + 1 < len(self.tokens) and self.tokens[pc+1][0] == '차차차':
                    val = self.variables.get('아쎄이', 0)
                    try:
                        print(chr(val), end='', flush=True)
                    except (ValueError, OverflowError):
                        raise MarineError(f"[줄 {line_num}] 런타임 오류: '아쎄이'에 유니코드로 변환 불가능한 수가 들어있다!")
                    pc += 2
                    continue
                    
                # 4. 조건문: (변수) 여쭤봐도 되겠습니까 필승
                if pc + 2 < len(self.tokens) and self.tokens[pc+1][0] == '여쭤봐도' and self.tokens[pc+2][0] == '되겠습니까':
                    var_name = token
                    self._check_variable(var_name, line_num)
                    val = self.variables[var_name]
                    if val == 0:
                        pc = self.jumps[pc+3] + 1
                    else:
                        pc += 4
                    continue
                        
                # 5. 반복문: (변수) 다시 알아보겠습니다 필승
                if pc + 2 < len(self.tokens) and self.tokens[pc+1][0] == '다시' and self.tokens[pc+2][0] == '알아보겠습니다':
                    var_name = token
                    self._check_variable(var_name, line_num)
                    val = self.variables[var_name]
                    if val == 0:
                        pc = self.jumps[pc+3] + 1
                    else:
                        pc += 4
                    continue
                        
                # 6. 블록 종료: 받아쓰
                if token == '받아쓰':
                    start_idx = self.jumps[pc]
                    if self.tokens[start_idx-2][0] == '다시':
                        pc = start_idx - 3
                    else:
                        pc += 1
                    continue
                        
                # 7. 덧셈 & 뺄셈: (변수1) (변수2) 돌격 / 역돌격
                if pc + 2 < len(self.tokens) and self.tokens[pc+2][0] in ('돌격', '역돌격'):
                    var1 = token
                    var2 = self.tokens[pc+1][0]
                    op = self.tokens[pc+2][0]
                    
                    self._check_variable(var1, line_num)
                    self._check_variable(var2, line_num)
                    
                    val1 = self.variables[var1]
                    val2 = self.variables[var2]
                    
                    if op == '돌격':
                        self.variables[var1] = val1 + val2
                    else:
                        self.variables[var1] = val1 - val2
                    pc += 3
                    continue
                    
                # 처리되지 않은 토큰은 건너뜀
                pc += 1
                
            except MarineError as e:
                print(f"\n{e}")
                break
            except Exception as e:
                print(f"\n[줄 {line_num}] 실행 중 알 수 없는 기열 오류 발생: {e}")
                break

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python interpreter.py <실행할파일.ak>")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            source_code = file.read()
            
        interpreter = MarineLangInterpreter(source_code)
        interpreter.run()
        
    except MarineError as e:
        print(f"\n{e}")
    except FileNotFoundError:
        print(f"\n[오류] '{file_path}' 파일을 찾을 수 없다! 파일이 탈영했다!")
    except Exception as e:
        print(f"\n[시스템 오류] {e}")