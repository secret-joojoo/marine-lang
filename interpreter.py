import sys
from modules.basic import BasicManager
from modules.supply import SupplyManager
from modules.music import MusicManager

class MarineError(Exception):
    """해병 언어 실행 중 발생하는 오도기합짜세 에러"""
    pass

class MarineLangInterpreter:
    def __init__(self, code: str):
        self.code = code
        self.tokens = []
        self.line_indents = {}
        self._tokenize()
        self.basic = BasicManager(MarineError)
        self.jumps = {}
        self.supply = SupplyManager(MarineError)
        self.music = MusicManager(MarineError, self.basic.parse_number)
        self._precompute_jumps()

    def _tokenize(self):
        """코드를 토큰으로 분리하고 각 줄의 들여쓰기를 기록한다!"""
        for line_num, line in enumerate(self.code.splitlines(), start=1):
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            self.line_indents[line_num] = indent
            for word in line.split():
                self.tokens.append((word, line_num))

    def _precompute_jumps(self):
        """조건문과 반복문의 블록 위치, 들여쓰기, 필수 키워드 누락을 빡세게 검사한다!"""
        stack = []
        for i, (token, line_num) in enumerate(self.tokens):

            if token == '여쭤봐도':
                if i + 1 < len(self.tokens) and self.tokens[i+1][0] == '되겠습니까':
                    if i + 2 >= len(self.tokens) or self.tokens[i+2][0] != '필승':
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '여쭤봐도 되겠습니까' 뒤에는 반드시 '필승'이 와야 한다! 기열!")

            elif token == '다시':
                if i + 1 < len(self.tokens) and self.tokens[i+1][0] == '알아보겠습니다':
                    if i + 2 >= len(self.tokens) or self.tokens[i+2][0] != '필승':
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '다시 알아보겠습니다' 뒤에는 반드시 '필승'이 와야 한다! 기열!")

            elif token == '필승':
                if i >= 2 and self.tokens[i-2][0] == '여쭤봐도':
                    stack.append(('IF', i, line_num, self.line_indents[line_num]))
                elif i >= 2 and self.tokens[i-2][0] == '다시':
                    stack.append(('WHILE', i, line_num, self.line_indents[line_num]))
                elif i >= 1 and self.tokens[i-1][0] == '있도록':
                    stack.append(('MUSIC_BLOCK', i, line_num, self.line_indents[line_num]))
                else:
                    raise MarineError(f"[줄 {line_num}] 구문 오류: '필승' 앞에는 '여쭤봐도 되겠습니까' 또는 '다시 알아보겠습니다'가 와야 한다! 악!")

            elif token == '받아쓰':
                if not stack:
                    raise MarineError(f"[줄 {line_num}] 구문 오류: '받아쓰'에 대응하는 '필승'이 없다! 기열!")
                block_type, start_idx, start_line, start_indent = stack.pop()
                self.jumps[start_idx] = i
                self.jumps[i] = start_idx

            else:
                if stack:
                    block_type, start_idx, start_line, start_indent = stack[-1]
                    is_first_token_of_line = (i == 0) or (self.tokens[i-1][1] != line_num)
                    if is_first_token_of_line and line_num > start_line:
                        if self.line_indents.get(line_num, 0) <= start_indent:
                            raise MarineError(f"[줄 {line_num}] 구문 오류: '필승'과 '받아쓰' 사이의 명령문은 반드시 들여쓰기가 되어야 한다! 악!")

        if stack:
            block_type, start_idx, start_line, start_indent = stack.pop()
            raise MarineError(f"[줄 {start_line}] 구문 오류: '필승'에 대응하는 '받아쓰'가 닫히지 않았다! 탈영인가!")

    def _parse_musician(self, token: str):
        """군악병N 토큰에서 순서(1부터)를 추출. 군악병 토큰이 아니면 None 반환."""
        if token.startswith('군악병') and len(token) > 3:
            rest = token[3:]
            if all(c == '!' for c in rest):
                return len(rest)
        return None

    def _parse_score_ref(self, token: str, line_num: int) -> int:
        """숙지완료하였습니다N 토큰에서 악보 순서(1부터)를 추출."""
        prefix = '숙지완료하였습니다'
        if token.startswith(prefix):
            rest = token[len(prefix):]
            if rest and all(c == '!' for c in rest):
                return len(rest)
        raise MarineError(f"[줄 {line_num}] 구문 오류: '{token}'은 올바른 악보 번호 표기가 아니다!")

    def run(self):
        """인터프리터 실행 (돌격!)"""
        pc = 0
        while pc < len(self.tokens):
            token, line_num = self.tokens[pc]

            try:
                # 1. 변수 선언: 신병 받아라 (정수)
                if token == '신병' and pc + 1 < len(self.tokens) and self.tokens[pc+1][0] == '받아라':
                    if pc + 2 >= len(self.tokens):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '신병 받아라' 뒤에 해병 정수가 오지 않았다!")
                    val_token = self.tokens[pc+2][0]
                    if not any(c in val_token for c in ['악', '!', '아']):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '신병 받아라' 뒤에 올바른 해병 정수가 오지 않았다!")
                    self.basic.declare(val_token, line_num)
                    pc += 3
                    continue

                # 2. 입력: 헤이빠빠리빠
                if token == '헤이빠빠리빠':
                    self.basic.receive_input(line_num)
                    pc += 1
                    continue

                # 3. 출력: 라이라이 차차차
                if token == '라이라이' and pc + 1 < len(self.tokens) and self.tokens[pc+1][0] == '차차차':
                    self.basic.print_output(line_num)
                    pc += 2
                    continue

                # 4. 조건문: (변수) 여쭤봐도 되겠습니까 필승
                if pc + 2 < len(self.tokens) and self.tokens[pc+1][0] == '여쭤봐도' and self.tokens[pc+2][0] == '되겠습니까':
                    var_name = token
                    self.basic.check_variable(var_name, line_num)
                    if self.basic.variables[var_name] == 0:
                        pc = self.jumps[pc+3] + 1
                    else:
                        pc += 4
                    continue

                # 5. 반복문: (변수) 다시 알아보겠습니다 필승
                if pc + 2 < len(self.tokens) and self.tokens[pc+1][0] == '다시' and self.tokens[pc+2][0] == '알아보겠습니다':
                    var_name = token
                    self.basic.check_variable(var_name, line_num)
                    if self.basic.variables[var_name] == 0:
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
                    if op == '돌격':
                        self.basic.add(var1, var2, line_num)
                    else:
                        self.basic.subtract(var1, var2, line_num)
                    pc += 3
                    continue

                # 8. 보급병 명령어 처리: 보급병! ~
                if token == '보급병!':
                    if pc + 1 >= len(self.tokens):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: 보급병 명령어가 불완전하다!")

                    cmd1 = self.tokens[pc+1][0]

                    if cmd1 == '과업':
                        if pc + 2 >= len(self.tokens) or self.tokens[pc+2][0] != '준비!':
                            raise MarineError(f"[줄 {line_num}] 구문 오류: '과업' 뒤에는 '준비!'가 와야 한다!")
                        self.supply.prepare()
                        pc += 3
                        continue

                    elif cmd1 == '창고로':
                        if pc + 2 >= len(self.tokens) or self.tokens[pc+2][0] != '이동':
                            raise MarineError(f"[줄 {line_num}] 구문 오류: '창고로' 뒤에는 '이동'이 와야 한다!")
                        self.supply.move_to_warehouse(line_num)
                        pc += 3
                        continue

                    elif pc + 2 < len(self.tokens) and self.tokens[pc+2][0] == '관리하겠습니다':
                        if pc + 4 >= len(self.tokens):
                            raise MarineError(f"[줄 {line_num}] 구문 오류: '관리하겠습니다' 뒤에 값 2개가 필요하다!")
                        warehouse = cmd1
                        val1 = self.basic.get_value(self.tokens[pc+3][0], line_num)
                        val2 = self.basic.get_value(self.tokens[pc+4][0], line_num)
                        self.supply.manage_warehouse(warehouse, val1, val2, line_num)
                        pc += 5
                        continue

                    elif pc + 2 < len(self.tokens) and self.tokens[pc+2][0] == '정리하겠습니다':
                        warehouse = cmd1
                        self.supply.clear_warehouse(warehouse, line_num)
                        pc += 3
                        continue

                    else:
                        raise MarineError(f"[줄 {line_num}] 구문 오류: 올바르지 않은 보급병 명령어다! 기열!")

                # 9. 보급병 창고 조사: (변수) (창고) 조사하겠습니다 (정수/변수)
                if pc + 2 < len(self.tokens) and self.tokens[pc+2][0] == '조사하겠습니다':
                    if pc + 3 >= len(self.tokens):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '조사하겠습니다' 뒤에 조사할 인덱스 값이 필요하다!")
                    target_var = token
                    warehouse = self.tokens[pc+1][0]
                    idx_val = self.basic.get_value(self.tokens[pc+3][0], line_num)
                    self.basic.check_variable(target_var, line_num)
                    result = self.supply.investigate_warehouse(warehouse, idx_val, line_num)
                    self.basic.variables[target_var] = result
                    pc += 4
                    continue

                # 10. 군악대 도열: 군악대 도열 (정수)
                if token == '군악대' and pc + 1 < len(self.tokens) and self.tokens[pc+1][0] == '도열':
                    if pc + 2 >= len(self.tokens):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '군악대 도열' 뒤에 정수가 오지 않았다!")
                    count = self.basic.parse_number(self.tokens[pc+2][0], line_num)
                    self.music.form_band(count, line_num)
                    pc += 3
                    continue

                # 11. 군악대! 명령어
                if token == '군악대!':
                    if pc + 1 >= len(self.tokens):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '군악대!' 뒤에 명령어가 없다!")
                    cmd = self.tokens[pc+1][0]
                    if cmd == '연주' and pc + 2 < len(self.tokens) and self.tokens[pc+2][0] == '시작':
                        self.music.play(line_num)
                        pc += 3
                        continue
                    elif cmd == '총원' and pc + 2 < len(self.tokens) and self.tokens[pc+2][0] == '헤쳐':
                        self.music.dismiss(line_num)
                        pc += 3
                        continue
                    elif cmd == '대기하겠습니다':
                        if pc + 2 >= len(self.tokens):
                            raise MarineError(f"[줄 {line_num}] 구문 오류: '대기하겠습니다' 뒤에 정수가 오지 않았다!")
                        seconds = self.basic.parse_number(self.tokens[pc+2][0], line_num)
                        self.music.set_delay(seconds, line_num)
                        pc += 3
                        continue
                    else:
                        instruments = []
                        j = pc + 1
                        while j < len(self.tokens) and self.tokens[j][0] != '준비':
                            instruments.append(self.tokens[j][0])
                            j += 1
                        if j >= len(self.tokens):
                            raise MarineError(f"[줄 {line_num}] 구문 오류: '군악대! ... 준비'에서 '준비'가 없다!")
                        self.music.set_instruments(instruments, line_num)
                        pc = j + 1
                        continue

                # 12. 악보 저장: 소중히 간직할 수 있도록 필승 ... 받아쓰
                if token == '소중히':
                    필승_idx = pc + 4
                    if (필승_idx >= len(self.tokens) or
                            self.tokens[pc+1][0] != '간직할' or
                            self.tokens[pc+2][0] != '수' or
                            self.tokens[pc+3][0] != '있도록' or
                            self.tokens[필승_idx][0] != '필승'):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '소중히 간직할 수 있도록 필승' 형식이 올바르지 않다!")
                    받아쓰_idx = self.jumps[필승_idx]
                    block_tokens = self.tokens[필승_idx+1:받아쓰_idx]
                    self.music.save_score(block_tokens, line_num)
                    pc = 받아쓰_idx + 1
                    continue

                # 13. 악보 숙지: 군악병N 제대로 숙지할 수 있도록 필승 숙지완료하였습니다M 받아쓰
                musician_idx = self._parse_musician(token)
                if musician_idx is not None:
                    필승_idx = pc + 5
                    if (필승_idx >= len(self.tokens) or
                            self.tokens[pc+1][0] != '제대로' or
                            self.tokens[pc+2][0] != '숙지할' or
                            self.tokens[pc+3][0] != '수' or
                            self.tokens[pc+4][0] != '있도록' or
                            self.tokens[필승_idx][0] != '필승'):
                        raise MarineError(f"[줄 {line_num}] 구문 오류: '{token} 제대로 숙지할 수 있도록 필승' 형식이 올바르지 않다!")
                    받아쓰_idx = self.jumps[필승_idx]
                    block_tokens = self.tokens[필승_idx+1:받아쓰_idx]
                    if len(block_tokens) != 1:
                        raise MarineError(f"[줄 {line_num}] 구문 오류: 악보 숙지 블록에는 악보 번호 하나만 있어야 한다!")
                    score_ref_token, score_ref_line = block_tokens[0]
                    score_idx = self._parse_score_ref(score_ref_token, score_ref_line)
                    self.music.learn_score(musician_idx, score_idx, line_num)
                    pc = 받아쓰_idx + 1
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
