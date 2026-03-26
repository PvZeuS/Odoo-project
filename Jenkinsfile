pipeline {
    agent any

    environment {
        EC2_USER     = 'ubuntu'
        EC2_IP       = branchIP()
        REMOTE_DIR   = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        
        COMPOSE_PROJECT_NAME = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        ODOO_PORT            = branchPort()
        POSTGRES_DB          = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        POSTGRES_USER        = 'odoo'
        // Extraemos el valor del credential para usarlo en los contenedores de test
        DB_PASS_SECRET       = credentials('odoo-db-password')
    }

    stages {
        stage('Linting') {
            steps {
                echo "--- INICIANDO LINTING DE CÓDIGO ---"
                // Ahora que docker funciona en Jenkins, esto no fallará
                sh 'docker run --rm -v $(pwd):/mnt vauxoo/odoo-linter:latest pylint --rcfile=/mnt/.pylintrc /mnt/addons'
            }
        }

        stage('Smart Unit Tests') {
            steps {
                script {
                    // Detectar si el commit trae el disparador MOD:nombre_modulo
                    def commitMsg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
                    def match = (commitMsg =~ /MOD:([a-zA-Z0-9_]+)/)
                    
                    if (match) {
                        def targetModule = match[0][1]
                        echo "--- EJECUTANDO TESTS PARA EL MÓDULO: ${targetModule} ---"
                        
                        sh """
                            # Crear red temporal para que Odoo y DB se hablen
                            docker network create test-net-${BUILD_NUMBER}
                            
                            # Levantar Postgres temporal
                            docker run -d --name db-test-${BUILD_NUMBER} \
                                --network test-net-${BUILD_NUMBER} \
                                -e POSTGRES_PASSWORD='${DB_PASS_SECRET}' \
                                -e POSTGRES_USER=odoo \
                                postgres:15-alpine
                            
                            # Esperar a que la DB esté lista
                            sleep 10
                            
                            # Ejecutar Odoo solo para instalar y testear el módulo indicado
                            docker run --rm --name odoo-test-${BUILD_NUMBER} \
                                --network test-net-${BUILD_NUMBER} \
                                -v \$(pwd)/addons:/mnt/extra-addons \
                                odoo:19.0 odoo \
                                -d odoo_test --db_host db-test-${BUILD_NUMBER} \
                                --db_user odoo --db_password='${DB_PASS_SECRET}' \
                                -i base,${targetModule} --test-enable --stop-after-init --log-level=test
                        """
                    } else {
                        echo "--- SALTANDO TESTS: No se detectó 'MOD:modulo' en el commit ---"
                    }
                }
            }
            post {
                always {
                    // Limpieza rigurosa de contenedores de prueba
                    sh """
                        docker stop db-test-${BUILD_NUMBER} || true
                        docker rm db-test-${BUILD_NUMBER} || true
                        docker network rm test-net-${BUILD_NUMBER} || true
                    """
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent(['ec2-odoo-key']) {
                    sh '''
                        echo "Desplegando rama ${BRANCH_NAME} en la IP ${EC2_IP}:${ODOO_PORT}..."
                        
                        # Subir archivos al servidor de destino
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "mkdir -p ${REMOTE_DIR}"
                        scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                        
                        # Ejecutar actualización remota
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << EOF
                            cd ${REMOTE_DIR}
                            export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
                            export ODOO_PORT=${ODOO_PORT}
                            export POSTGRES_DB=${POSTGRES_DB}
                            export POSTGRES_USER=${POSTGRES_USER}
                            export POSTGRES_PASSWORD='${DB_PASS_SECRET}'
                            
                            docker compose up -d --build --remove-orphans
                            sleep 15
                            docker compose run --rm odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init
                            docker compose restart odoo
EOF
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "--- ¡TODO OK! ---"
            echo "Acceso: http://${EC2_IP}:${ODOO_PORT}"
        }
        failure {
            echo "--- EL PIPELINE FALLÓ ---"
            echo "Revisa si el commit tiene errores de sintaxis (Linting) o si los tests no pasaron."
        }
    }
}

def branchIP() {
    return (env.BRANCH_NAME == 'main') ? '3.144.231.64' : '18.219.33.101'
}

def branchPort() {
    return (env.BRANCH_NAME == 'main') ? '8071' : '8070'
}