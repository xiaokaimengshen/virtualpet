import json
import urllib.error
import urllib.request

import DyberPet.settings as settings


class LocalLLMService:
    """Remote LLM gateway (kept class name for compatibility)."""

    @staticmethod
    def _cfg():
        cfg = settings.llm_config if isinstance(settings.llm_config, dict) else {}
        merged = settings.LLM_CONFIG_DEFAULT.copy()
        merged.update(cfg)
        return merged

    def unavailable_reason(self):
        cfg = self._cfg()
        if not cfg.get('enabled', False):
            return '大模型未启用，请在系统设置中开启。'

        provider = cfg.get('api_type', '')
        model = (cfg.get('model') or '').strip()
        api_url = (cfg.get('api_url') or '').strip()
        api_key = (cfg.get('api_key') or '').strip()

        if provider not in settings.LLM_PROVIDERS:
            return '未选择有效的模型服务商。'
        if not model:
            return '未配置模型名称。'
        if not api_url:
            return '未配置 API 地址。'
        if provider != 'custom' and not api_key:
            return '未配置 API 密钥。'
        return None

    def quick_check(self):
        reason = self.unavailable_reason()
        if reason:
            return False, reason
        try:
            text = self.chat(
                messages=[{'role': 'user', 'content': '你好'}],
                system_prompt='你是测试助手。',
                max_tokens=12,
                temperature=0.1,
                timeout=10,
            )
            if text:
                return True, '联网大模型连接成功。'
            return False, '连接成功，但返回内容为空。'
        except Exception as e:
            return False, f'连接失败: {e}'

    def chat(self, messages, system_prompt=None, max_tokens=256, temperature=0.6, timeout=15):
        cfg = self._cfg()
        model = cfg.get('model', '')
        api_url = (cfg.get('api_url') or '').strip().rstrip('/')
        api_key = (cfg.get('api_key') or '').strip()

        payload_messages = list(messages)
        if system_prompt:
            payload_messages = [{'role': 'system', 'content': system_prompt}] + payload_messages

        endpoint = api_url + '/chat/completions'
        payload = {
            'model': model,
            'messages': payload_messages,
            'temperature': float(temperature),
            'max_tokens': int(max_tokens),
        }

        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        raw = self._post_json(endpoint, payload, headers=headers, timeout=timeout)
        data = json.loads(raw)
        choices = data.get('choices') or []
        if choices:
            msg = choices[0].get('message') or {}
            return (msg.get('content') or '').strip()
        return ''

    def pet_interaction_reply(self, event_name, user_text='', pet_name='桌宠'):
        prompt = (
            f'你是桌宠{pet_name}，请根据互动事件简短回复一句中文，12字以内，口吻可爱，避免emoji。'
            f' 事件: {event_name}。'
        )
        if user_text:
            prompt += f' 用户输入: {user_text}。'

        reply = self.chat(
            messages=[{'role': 'user', 'content': prompt}],
            system_prompt='你是桌面宠物的即时对话内核。回复要短，不要解释。',
            max_tokens=64,
            temperature=0.8,
            timeout=10,
        )
        return reply.strip()

    @staticmethod
    def _post_json(url, payload, headers=None, timeout=15):
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=body,
            headers=headers or {'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', errors='ignore') if hasattr(e, 'read') else ''
            raise RuntimeError(f'HTTP {e.code}: {raw or e.reason}')
