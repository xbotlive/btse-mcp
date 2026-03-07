import { readdir, readFile } from 'fs/promises';
import { join } from 'path';
import { parse } from 'yaml';

interface SkillFrontmatter {
  name: string;
  description: string;
}

interface ValidationResult {
  skill: string;
  valid: boolean;
  errors: string[];
}

const SKILLS_DIR = join(import.meta.dirname, '..', 'skills');

async function findSkillFiles(dir: string): Promise<string[]> {
  const files: string[] = [];
  const entries = await readdir(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      const subFiles = await findSkillFiles(fullPath);
      files.push(...subFiles);
    } else if (entry.name === 'SKILL.md') {
      files.push(fullPath);
    }
  }

  return files;
}

function extractFrontmatter(
  content: string,
): { frontmatter: string; body: string } | null {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return null;
  return { frontmatter: match[1], body: match[2] };
}

function validateSkill(skillPath: string, content: string): ValidationResult {
  const errors: string[] = [];
  const relativePath = skillPath.replace(SKILLS_DIR + '/', 'skills/');

  // 1. Frontmatter must exist and parse
  const extracted = extractFrontmatter(content);
  if (!extracted) {
    return {
      skill: relativePath,
      valid: false,
      errors: ['Missing or invalid YAML frontmatter (must be between --- lines)'],
    };
  }

  let frontmatter: SkillFrontmatter;
  try {
    frontmatter = parse(extracted.frontmatter) as SkillFrontmatter;
  } catch (error) {
    return {
      skill: relativePath,
      valid: false,
      errors: [`Invalid YAML in frontmatter: ${(error as Error).message}`],
    };
  }

  // 2. name: required, lowercase-hyphen only, must match folder name
  const folderName = skillPath.split('/').slice(-2)[0];
  if (!frontmatter.name) {
    errors.push('Missing required field: name');
  } else if (typeof frontmatter.name !== 'string') {
    errors.push('Field "name" must be a string');
  } else if (!/^[a-z0-9-]+$/.test(frontmatter.name)) {
    errors.push('Field "name" must be lowercase with hyphens only (e.g., "btse-placing-orders")');
  } else if (frontmatter.name !== folderName) {
    errors.push(
      `Field "name" (${frontmatter.name}) must match folder name (${folderName})`,
    );
  }

  // 3. description: required, 10–200 chars
  if (!frontmatter.description) {
    errors.push('Missing required field: description');
  } else if (typeof frontmatter.description !== 'string') {
    errors.push('Field "description" must be a string');
  } else if (frontmatter.description.length < 10) {
    errors.push('Field "description" must be at least 10 characters');
  } else if (frontmatter.description.length > 200) {
    errors.push('Field "description" must be at most 200 characters');
  }

  // 4. Body must have actual content
  if (!extracted.body.trim()) {
    errors.push('Skill has no content after frontmatter');
  }

  // 5. Body must have at least one heading
  if (!extracted.body.includes('# ') && !extracted.body.includes('## ')) {
    errors.push('Skill body should contain at least one heading (# or ##)');
  }

  return { skill: relativePath, valid: errors.length === 0, errors };
}

async function main(): Promise<void> {
  console.log('🔍 Validating btse-mcp Skills...\n');

  const skillFiles = await findSkillFiles(SKILLS_DIR);

  if (skillFiles.length === 0) {
    console.error('❌ No SKILL.md files found in skills/ directory');
    process.exit(1);
  }

  console.log(`Found ${skillFiles.length} skill(s)\n`);

  const results: ValidationResult[] = [];

  for (const skillFile of skillFiles.sort()) {
    const content = await readFile(skillFile, 'utf-8');
    results.push(validateSkill(skillFile, content));
  }

  let validCount = 0;
  let invalidCount = 0;

  for (const result of results) {
    if (result.valid) {
      console.log(`✅  ${result.skill}`);
      validCount++;
    } else {
      console.log(`❌  ${result.skill}`);
      for (const error of result.errors) {
        console.log(`    - ${error}`);
      }
      invalidCount++;
    }
  }

  console.log(`\n${'─'.repeat(50)}`);
  console.log(`\n📊  ${validCount} valid  |  ${invalidCount} invalid\n`);

  if (invalidCount > 0) {
    process.exit(1);
  }

  console.log('✓ All skills valid\n');
}

main().catch((error) => {
  console.error('Validation error:', error);
  process.exit(1);
});
