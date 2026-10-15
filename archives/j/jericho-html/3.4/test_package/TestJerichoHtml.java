import net.htmlparser.jericho.Element;
import net.htmlparser.jericho.Source;
import net.htmlparser.jericho.TextExtractor;

import java.util.List;

/**
 * TestJerichoHtml — jericho-html API 调用测试
 *
 * 使用 Source/Element/TextExtractor API 解析 HTML 字符串，
 * 验证 jericho-html 库的核心功能正常工作（R34 实质性验证）。
 */
public class TestJerichoHtml {
    public static void main(String[] args) throws Exception {
        String html = "<html><head><title>Test Page</title></head>"
                + "<body><p class=\"intro\">Hello <b>World</b></p>"
                + "<a href=\"https://example.com\">link</a></body></html>";

        Source source = new Source(html);

        // 断言 1: 能取到 title 元素
        List<Element> titles = source.getAllElements("title");
        if (titles.size() != 1) {
            System.err.println("FAIL: Expected 1 title element, got " + titles.size());
            System.exit(1);
        }

        // 断言 2: title 文本内容正确
        if (!"Test Page".equals(titles.get(0).getContent().toString())) {
            System.err.println("FAIL: Unexpected title content: "
                    + titles.get(0).getContent());
            System.exit(1);
        }

        // 断言 3: p 元素的 class 属性值正确
        Element p = source.getFirstElement("p");
        if (p == null || !"intro".equals(p.getAttributeValue("class"))) {
            System.err.println("FAIL: Unexpected p class attribute");
            System.exit(1);
        }

        // 断言 4: a 元素的 href 属性值正确
        Element a = source.getFirstElement("a");
        if (a == null || !"https://example.com".equals(a.getAttributeValue("href"))) {
            System.err.println("FAIL: Unexpected a href attribute");
            System.exit(1);
        }

        // 断言 5: TextExtractor 提取全部可见文本
        String text = new TextExtractor(source).toString();
        if (!text.contains("Test Page") || !text.contains("Hello")
                || !text.contains("World")) {
            System.err.println("FAIL: TextExtractor output missing content: " + text);
            System.exit(1);
        }

        // 断言 6: 元素在源文本中的位置可追踪（jericho 核心特性）
        if (p.getBegin() <= titles.get(0).getBegin() || p.getEnd() <= p.getBegin()) {
            System.err.println("FAIL: Element positions not tracked correctly");
            System.exit(1);
        }

        System.out.println("PASS: jericho-html API 调用测试全部通过");
    }
}
