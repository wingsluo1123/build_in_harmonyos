/*
 * Consumer fixture for the vtable-dumper end-to-end check (rule 12).
 *
 * This is a real C++ shared library with two polymorphic classes. The tool
 * under test must recover their virtual tables from the *built* .so, so the
 * assertions in test.sh compare the tool output against the virtual member
 * functions declared here.
 *
 * Build: clang++ -shared -fPIC -o libvtable_consumer.so vtable_consumer.cpp
 */

class Document {
public:
    virtual ~Document();
    virtual double sizeKiB() const;
    virtual const char* kind() const;
};

class Invoice : public Document {
public:
    ~Invoice() override;
    double sizeKiB() const override;
    const char* kind() const override;
    virtual int lineCount() const;
};

Document::~Document() {}
double Document::sizeKiB() const { return 0.0; }
const char* Document::kind() const { return "document"; }

Invoice::~Invoice() {}
double Invoice::sizeKiB() const { return 12.5; }
const char* Invoice::kind() const { return "invoice"; }
int Invoice::lineCount() const { return 7; }

extern "C" Document* document_factory(const char* kind)
{
    if (kind && kind[0] == 'i') {
        return new Invoice();
    }
    return new Document();
}
