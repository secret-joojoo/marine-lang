import sys

class MarineLangInterpreter:
    def __init__(self, code: str):
        self.code = code
        self.tokens = []
        self._tokenize()
        self.variables = {'아쎄이': 0}
        self.var_count = 0
        self.jumps = {}
        self._precompute_jumps()

    def _tokenize(self):
        """코드를 토큰으로 분리하고 각 토큰의 줄 번호를 기록합니다."""
        for line_num, line in enumerate(self.code.splitlines(), start=1):
            for word in line.split():
                self.tokens.append((word, line_num))

    def _precompute_jumps(self):
        """조건문과 반복문의 블록 위치를 계산하며 짝이 맞지 않을 경우 줄 번호와 함께 예외를 발생시킵니다."""
        stack = []
        for i, (token, line_num) in enumerate(self.tokens):
            if token == '필승':
                if i >= 2 and self.tokens[i-2][0] == '여쭤봐도':
                    stack.append(('IF', i, line_num))
                elif i >= 2 and self.tokens[i-2][0] == '다시':
                    stack.append(('WHILE', i, line_num))
                else:
                    raise SyntaxError(f"[줄 {line_num}] 구문 오류: '필승' 앞에는 '여쭤봐도 되겠습니까' 또는 '다시 알아보겠습니다'가 와야 합니다.")
            elif token == '받아쓰':
                if not stack:
                    raise SyntaxError(f"[줄 {line_num}] 구문 오류: '받아쓰'에 대응하는 '필승'이 없습니다.")
                block_type, start_idx, start_line = stack.pop()
                self.jumps[start_idx] = i
                self.jumps[i] = start_idx
        
        if stack:
            block_type, start_idx, start_line = stack.pop()
            raise SyntaxError(f"[줄 {start_line}] 구문 오류: '필승'에 대응하는 '받아쓰'가 닫히지 않았습니다.")

    def _parse_number(self, s: str, line_num: int) -> int:
        """정수를 파싱합니다. 형식이 어긋날 경우 0을 반환합니다."""
        is_negative = s.startswith('아')
        if is_negative:
            s = s[1:]
        
        if not s or not s.startswith('악'):
            return 0
            
        parts = s.split('악')[1:]
        digits = [str(len(p)) for p in parts]
        try:
            val = int("".join(digits))
            return -val if is_negative else val
        except ValueError:
            return 0

    def run(self):
        """토큰을 순차적으로 읽으며 명령을 수행합니다. 오류 발생 시 줄 번호를 출력합니다."""
        pc = 0
        while pc < len(self.tokens):
            token, line_num = self.tokens[pc]
            
            try:
                # 1. 변수 선언: 신병 받아라 (정수)
                if token == '신병' and pc + 2 < len(self.tokens) and self.tokens[pc+1][0] == '받아라':
                    val = self._parse_number(self.tokens[pc+2][0], line_num)
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
                        pass
                    pc += 1
                    continue
                    
                # 3. 출력: 라이라이 차차차
                if token == '라이라이' and pc + 1 < len(self.tokens) and self.tokens[pc+1][0] == '차차차':
                    val = self.variables.get('아쎄이', 0)
                    try:
                        print(chr(val), end='', flush=True)
                    except ValueError:
                        print(f"\n[줄 {line_num}] 런타임 오류: 출력할 수 없는 유니코드 값입니다. (값: {val})")
                    pc += 2
                    continue
                    
                # 4. 조건문: (변수) 여쭤봐도 되겠습니까 필승
                if pc + 2 < len(self.tokens) and self.tokens[pc+1][0] == '여쭤봐도' and self.tokens[pc+2][0] == '되겠습니까':
                    var_name = token
                    val = self.variables.get(var_name, 0)
                    if val == 0:
                        pc = self.jumps[pc+3] + 1
                    else:
                        pc += 4
                    continue
                        
                # 5. 반복문: (변수) 다시 알아보겠습니다 필승
                if pc + 2 < len(self.tokens) and self.tokens[pc+1][0] == '다시' and self.tokens[pc+2][0] == '알아보겠습니다':
                    var_name = token
                    val = self.variables.get(var_name, 0)
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
                    
                    val1 = self.variables.get(var1, 0)
                    val2 = self.variables.get(var2, 0)
                    
                    if op == '돌격':
                        self.variables[var1] = val1 + val2
                    else:
                        self.variables[var1] = val1 - val2
                    pc += 3
                    continue
                    
                # 처리되지 않은 토큰은 건너뜀
                pc += 1
                
            except Exception as e:
                print(f"\n[줄 {line_num}] 실행 중 알 수 없는 오류 발생: {e}")
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
        
    except SyntaxError as e:
        print(f"\n[컴파일 오류] {e}")
    except FileNotFoundError:
        print(f"\n[오류] '{file_path}' 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"\n[시스템 오류] {e}")